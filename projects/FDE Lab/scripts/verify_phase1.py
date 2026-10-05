"""Repeatable Phase 1 acceptance probe, run from any directory.

Preserved from the 2026-10-03 independent verifier recorded in docs/verification.md.
Instructor-only: the alternative SQL and scripted reasoning are test inputs, not
learner evidence. Every state mutation and exercise occurs in a temporary profile.
No sibling system, model endpoint or default progress profile is invoked.
"""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
from tempfile import TemporaryDirectory

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from lab.contracts import PRIVATE_FIELDS, load_scenario
from lab.engine import Engine
from lab.store import fresh_state
from lab import exercise

SCENARIO = load_scenario()
checks = []
command_count = 0

def require(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)

# An alternative query, authored independently of the product test repair.
SQL = '''WITH current_orders AS (
  SELECT DISTINCT o.* FROM raw_orders o
  JOIN (SELECT order_id, MAX(version) AS v FROM raw_orders GROUP BY order_id) x
    ON x.order_id=o.order_id AND x.v=o.version
), current_refunds AS (
  SELECT DISTINCT r.* FROM raw_refunds r
  JOIN (SELECT event_id, MAX(version) AS v FROM raw_refunds GROUP BY event_id) x
    ON x.event_id=r.event_id AND x.v=r.version
), refunds AS (
  SELECT order_id, SUM(amount_cents) AS cents FROM current_refunds GROUP BY order_id
)
SELECT SUBSTR(o.occurred_at,1,10) AS report_date,
       SUM(o.amount_cents-COALESCE(r.cents,0)) AS net_revenue_cents
FROM current_orders o LEFT JOIN refunds r ON r.order_id=o.order_id
WHERE o.status='completed'
GROUP BY SUBSTR(o.occurred_at,1,10);'''

with TemporaryDirectory(prefix='fde-independent-cli-') as temp:
    directory = Path(temp)
    state_file = directory / 'state.json'
    def state():
        return json.loads(state_file.read_text())
    def run(*tokens, ok=True):
        global command_count
        command_count += 1
        result = subprocess.run([str(PROJECT/'fde'), '--state-dir', str(directory), *tokens],
            cwd=PROJECT, text=True, capture_output=True, timeout=8)
        expected = 0 if ok else 2
        require(result.returncode == expected, 'CLI exit contract: '+tokens[0]+' stderr='+result.stderr+' stdout='+result.stdout)
        return result.stdout if ok else result.stderr
    def submit(kind, evidence, concept=None, dimension=None):
        run(kind, 'Synthetic verification reasoning: inspect the cited observations, separate assumptions, and name a falsifying check.', '--evidence', evidence)
        sid = state()['submissions'][-1]['id']
        args = ['review', sid, '--result', 'demonstrated', '--note',
            'Synthetic independent verification input; assesses transition behavior only, not learner competence.',
            '--tutor', 'Independent verifier (synthetic)']
        if concept:
            args += ['--concept', concept]
        if dimension:
            args += ['--dimension', dimension]
        run(*args)
        return sid

    opening = run('next')
    require(opening.strip() == SCENARIO['opening'], 'opening matches frozen customer facts')
    require(opening.rstrip().endswith('What do you want to understand first, and why?'), 'opening ends with learner question')
    require(state()['released']==[] and state()['reviews']==[], 'opening has no released artifacts or judgments')
    initial = state_file.read_bytes()
    run('investigate', 'quality-report', ok=False)
    require(state_file.read_bytes()==initial, 'locked investigation preserves state')
    run('evidence', 'warehouse-sample', ok=False)
    run('build', ok=False)
    require(not (directory/'workspace').exists(), 'premature build creates no solution or fixture')
    unknown = run('ask', 'cto', 'The chair needs remodeling')
    require('more specific question' in unknown and state()['released']==[], 'irrelevant substring does not release evidence')
    run('ask', 'finance', 'What is net revenue and which workflow depends on it?')
    require(state()['released']==['semantic-contract'], 'multi-topic question releases one selected topic')
    hypothesis = run('hypothesis', 'I would compare two observed paths before replacing a component.')
    require('YOU IDENTIFIED' in hypothesis and state()['reviews']==[], 'reasoning saved pending attributed assessment')
    require(state()['submissions'][-1]['text'].startswith('I would compare'), 'learner text persists across processes')

    public = [opening, run('diagram'), run('progress'), run('map'), run('log')]
    for component in SCENARIO['components']:
        result = run('open',component)
        require(SCENARIO['components'][component]['question'] in result, 'box has a causal question: '+component)
        public.append(result)
    for key in PRIVATE_FIELDS:
        value = SCENARIO[key]
        if isinstance(value,str):
            require(all(value not in output for output in public), 'private field withheld: '+key)
        elif isinstance(value,list):
            require(all(sentence not in output for sentence in value for output in public), 'private list withheld: '+key)

    # Release every authored card through the public investigator in prerequisite order.
    todo = set(SCENARIO['evidence'])-set(state()['released'])
    while todo:
        ready = [key for key in sorted(todo) if set(SCENARIO['evidence'][key]['requires'])<=set(state()['released'])]
        require(bool(ready), 'all authored evidence reachable through valid gates')
        for key in ready:
            output = run('investigate',key)
            require('['+key+']' in output and key in state()['released'], 'requested artifact identity preserved: '+key)
            todo.remove(key)
    require(len(state()['released'])==len(SCENARIO['evidence']), 'all thirteen artifacts reached without hidden projection')

    submit('frame','business-workflow',dimension='Discovery')
    require(state()['phase']=='DISCOVERY','frame alone does not scope')
    submit('requirements','semantic-contract,operating-targets',dimension='Requirements')
    require(state()['phase']=='SCOPED','reviewed frame and requirements scope')
    run('design','Synthetic design explains boundaries and a small executable test.','--evidence','semantic-contract,source-contract')
    design_id = state()['submissions'][-1]['id']
    require(state()['phase']=='DESIGNING','saved design still awaits assessment')
    run('build',ok=False)
    run('review',design_id,'--result','demonstrated','--note','Synthetic independent transition assessment.','--tutor','Independent verifier (synthetic)','--concept','data-grain')
    require(state()['phase']=='PROTOTYPING','reviewed design opens prototype')
    run('build')
    workspace = directory/'workspace'
    baseline_fixture = (workspace/'fixture.sql').read_bytes()
    require((workspace/'revenue.sql').read_text()==exercise.starter(),'build gives broken authored artifact, no repair')
    run('test')
    require(not state()['exercise']['passed'] and state()['phase']=='PROTOTYPING','broken starter fails and blocks progress')
    (workspace/'revenue.sql').write_text(SQL)
    run('test')
    require(state()['exercise']['passed'] and len(state()['exercise']['checks'])==8,'independent SQL passes eight varied oracle cases')
    require(state()['phase']=='EVALUATING','passing prototype enters evaluation')
    event_id = state()['events'][-1]['id']
    submit('evaluate',event_id,concept='data-grain')
    require(state()['phase']=='HARDENING','reviewed evaluation opens failure work')
    original = (workspace/'revenue.sql').read_bytes()
    run('break')
    require((workspace/'revenue.sql').read_bytes()==original,'failure injection preserves learner repair')
    require((workspace/'incident.sql').exists() and 'incident-logs' not in state()['released'],'incident branch created with logs gated')
    run('test')
    require(not state()['incident_passed'],'injected failure is executable and reproduced')
    run('investigate','incident delivery log')
    require('incident-logs' in state()['released'],'incident telemetry released on request')
    (workspace/'incident.sql').write_text(SQL)
    run('test')
    require(state()['incident_passed'] and len(state()['exercise']['checks'])==16,'independent repair passes sixteen replay checks')
    event_id = state()['events'][-1]['id']
    submit('debug','incident-logs,'+event_id,concept='data-grain',dimension='Debugging')
    submit('debug','incident-logs,'+event_id,concept='idempotency',dimension='Reliability')
    submit('harden','operating-targets,access-boundary,incident-logs',dimension='Delivery')
    require(state()['phase']=='DEPLOYING','readiness and debugging gates passed')
    (workspace/'incident.sql').write_text(SQL+'\n-- edit after validation\n')
    saved = state_file.read_bytes()
    run('deploy',ok=False)
    require(state_file.read_bytes()==saved and state()['phase']=='DEPLOYING','stale artifact cannot deploy or mutate progress')
    run('test')
    run('deploy')
    require(state()['phase']=='OPERATING' and 'pilot-results' not in state()['released'],'simulated rollout still gates observations')
    pilot = run('investigate','pilot adoption measurement')
    require(SCENARIO['pilot']['text'] in pilot,'pilot facts come from frozen scenario contract')
    require('30' in SCENARIO['evidence']['business-baseline']['text'] and '30' in pilot,'pilot baseline matches discovery evidence')
    submit('measure','pilot-results,business-baseline',dimension='Business Impact')
    require(state()['phase']=='MEASURING','reviewed customer measurement advances')
    submit('explain','pilot-results,incident-logs',dimension='Communication')
    require(state()['phase']=='RETROSPECTIVE','reviewed explanation enters retrospective')
    require(all(r['state']!='MASTERED' for r in state()['concepts'].values()),'passing exercise alone grants no mastery')

    recalls = {}
    for index in range(len(SCENARIO['recall'])):
        first = run('recall')
        pending = state()['pending_recall']
        second = run('recall')
        require(first==second and state()['pending_recall']==pending,'unanswered recall stays stable')
        prompt = next(p for p in SCENARIO['recall'] if p['id']==pending)
        run('answer','Synthetic verification transfer explanation.','--kind','recall')
        sid = state()['submissions'][-1]['id']
        require(state()['submissions'][-1]['prompt']==pending,'saved recall links exact requested prompt')
        wrong = next(c for c in SCENARIO['technical_concepts'] if c!=prompt['concept'])
        saved = state_file.read_bytes()
        run('review',sid,'--result','demonstrated','--note','Wrong concept probe.','--tutor','Independent verifier (synthetic)','--concept',wrong,ok=False)
        require(state_file.read_bytes()==saved,'invalid concept review is atomic')
        run('review',sid,'--result','demonstrated','--note','Synthetic transfer probe; not learner mastery evidence.','--tutor','Independent verifier (synthetic)','--concept',prompt['concept'])
        recalls[pending]=sid
    require(state()['concepts']['data-grain']['state']=='MASTERED' and state()['concepts']['idempotency']['state']=='MASTERED','distinct transfer and debugging attestations can establish scoped completion')
    require(state()['phase']=='MASTERED','two scoped concepts complete synthetic engagement')
    sid = recalls['shipment-lines']
    run('review',sid,'--result','developing','--note','Synthetic reassessment contradicts this prior transfer.','--tutor','Independent verifier (synthetic)','--concept','data-grain')
    require(state()['concepts']['data-grain']['state']!='MASTERED' and state()['phase']=='RETROSPECTIVE','developing reassessment reopens concept and engagement')
    summary = run('end')
    require(all(label in summary for label in ('WHAT YOU SOLVED','WHAT YOU UNDERSTOOD','WHAT YOU MISSED','ONE IMPORTANT MENTAL MODEL','WHAT WILL REAPPEAR LATER')),'session reflection includes scoped evidence and recall')

    before_reset = state_file.read_bytes()
    branch_before = (workspace/'incident.sql').read_bytes()
    reset_opening = run('reset')
    require(reset_opening==opening,'reset reproduces exact opening')
    archive = directory/'history/reset-0001'
    require((archive/'state.json').read_bytes()==before_reset,'reset archives exact prior answers and reviews')
    require((archive/'workspace/incident.sql').read_bytes()==branch_before,'reset archives exact learner SQL')
    require(state()['released']==[] and state()['submissions']==[] and state()['reviews']==[],'fresh run has no fabricated history')
    fresh_after_reset = state_file.read_bytes()
    run('reset')
    require(state_file.read_bytes()==fresh_after_reset,'repeated reset yields deterministic started state')
    run('investigate','semantic-contract')
    run('investigate','business-workflow')
    submit('frame','business-workflow')
    submit('requirements','semantic-contract')
    submit('design','semantic-contract')
    run('build')
    require((workspace/'fixture.sql').read_bytes()==baseline_fixture,'reset rebuild reproduces exact fixture')

    # Source boundaries are inspected independently of descriptive registry claims.
    external_imports = []
    for path in (PROJECT/'lab').rglob('*.py'):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                external_imports.extend(alias.name for alias in node.names if alias.name.startswith(('py_dev','data_system_map','data_modeling_lab','quality_system','training')))
            elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module and node.module.startswith(('py_dev','data_system_map','data_modeling_lab','quality_system','training')):
                external_imports.append(node.module)
    require(not external_imports,'product imports no sibling or AI-OS execution package')
    registry=json.loads((PROJECT/'integrations/registry.json').read_text())
    require(registry['execution_enabled'] is False and registry['connection_policy']=='reference-only','registry remains nonexecuting reference data')
    run('integrations')
    shell=subprocess.run([str(PROJECT/'fde'),'--state-dir',str(directory),'shell'],input='progress\nexit\n',text=True,capture_output=True,cwd=PROJECT,timeout=8)
    require(shell.returncode==0 and 'fde>' in shell.stdout,'actual launcher opens and exits command shell')

# A separate in-memory canary checks explicit public projection, without calling solution.
with TemporaryDirectory(prefix='fde-independent-projection-') as directory:
    scenario=json.loads(json.dumps(SCENARIO))
    canary='VERIFIER-PRIVATE-CANARY-1937'
    for key in PRIVATE_FIELDS:
        scenario[key]=canary
    engine=Engine(scenario,fresh_state(scenario),directory)
    outputs=[engine.start(),engine.diagram(),engine.progress(),engine.graph(),engine.log()]
    outputs += [engine.open(key) for key in scenario['components']]
    require(all(canary not in out for out in outputs),'all normal projections withhold instructor-only canary')

print(json.dumps({'result':'PASS','assertions':len(checks),'cli_commands':command_count,'scenario_count':1,'components':len(SCENARIO['components']),'evidence_cards':len(SCENARIO['evidence']),'recall_prompts':len(SCENARIO['recall']),'alternate_sql_base_cases':8,'alternate_sql_replay_cases':16,'temporary_profiles_removed':True},indent=2))
