"""Repeatable Step 3 acceptance over synthetic, isolated learner profiles.

Reference prose is authored material, never evidence of learner judgment.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.problems import PROBLEMS,PROBLEM_MAP,validate_problem,learner_problem
from lab.business_reasoning import evaluate,expected_for,workbook
from lab.reasoning_fixtures import VARIANTS,fixture
from lab.learning_engine import LearningEngine
from lab.store import Store
from lab.sql_lab.contracts import fingerprint

BANK=[p for p in PROBLEMS if p['kind']=='reasoning']

def reference_answer(p,variant='sample',policy=None):
 policy=policy or next(iter(p['evaluation_rules']['policies']))
 text=p['evaluation_rules']['resolution']
 return {'reason':text,'policy':policy,'facts':expected_for(p,variant,policy),'decision':text,
  'metric_contract':{f:text for f in p['evaluation_rules']['metric_fields']},
  'assumptions':[{'claim':'Apply the named exercise contract to the displayed extract.','status':'documented','impact':'An alternative contract requires a separately labeled result.'}],
  'diagnosis':p['evaluation_rules']['common_error'],'repair':text}

def prepare(engine,r):
 r=engine.action(r,'predict',{'prediction':'Which business decision is this report intended to change, and who owns that decision?'})
 return engine.action(r,'prepare',{'requirements':'Clarify the consumer, population, clock and acceptance tests.',
  'input_grain':'Separate the displayed business entities, received events and effective versions.',
  'output_grain':'A labeled result at the declared consumer entity and reporting clock.',
  'proposal':'Resolve identities and eligibility before aggregating; reconcile components and communicate uncertainty.'})

def validate():
 assert len(BANK)==60
 assert set(Counter(p['artifacts']['area'] for p in BANK).values())=={6}
 definitions=[];objectives=0;mutants=0;workflows=0
 for p in BANK:
  validate_problem(p)
  peer=PROBLEM_MAP[p['transfer_from']]
  assert peer['domain']!=p['domain'] and set(peer['mastery_tags'])&set(p['mastery_tags'])
  for mode in p['modes']:
   public=learner_problem(p,mode)
   assert 'expected_output_grain' not in public and 'evaluation_rules' not in public
   assert 'candidate_reasoning' not in public['artifacts'] and 'workbook' not in public['artifacts']
   assert p['solution'] not in json.dumps(public)
  for variant in VARIANTS:
   for policy in p['evaluation_rules']['policies']:
    answer=reference_answer(p,variant,policy);e=evaluate(p,answer,variant)
    assert e['status']=='REVIEW_REQUIRED' and e['objective_status']=='PASS'
    objectives+=1
    for check in p['evaluation_rules']['checks']:
     wrong=deepcopy(answer);kind=check['type'];value=wrong['facts'][check['field']]
     wrong['facts'][check['field']]=['wrong_identity'] if kind=='keys' else 'wrong_relationship' if kind=='text' else 999999 if value is None else None
     assert evaluate(p,wrong,variant)['status']=='FAIL'
     mutants+=1
  definitions.append({'problem_id':p['problem_id'],'domain':p['domain'],'area':p['artifacts']['area'],'difficulty':p['difficulty']['level'],
   'definition_sha256':fingerprint(p),'variants':len(VARIANTS),'policies':list(p['evaluation_rules']['policies']),
   'objective_fields':[c['field'] for c in p['evaluation_rules']['checks']],'transfer_problem':p['transfer_from']})
 with TemporaryDirectory(prefix='ae-business-acceptance-') as directory:
  for mode in ('LEARN','PRACTICE','INTERVIEW'):
   engine=LearningEngine(Store(Path(directory)/mode))
   assert len(engine.catalog(mode,'reasoning'))==60
   for p in BANK:
    r=engine.start(p['problem_id'],mode)
    assert r['fixture_variant']=='sample'
    for variant in VARIANTS:
     assert r['fixture_variant']==variant
     v=engine.view(r)
     assert v['problem']['sample_rows']=={t['name']:fixture(p['domain'],variant)[t['name']] for t in p['tables']}
     r=engine.action(prepare(engine,r),'submit',reference_answer(p,variant))
     assert r['state']=='REVIEW_PENDING'
     # Numeric agreement cannot manufacture judgment/application evidence.
     assert not any(e['kind']=='applied' for e in engine.mastery.evidence() if e['reference']==r['attempts'][-1]['attempt_id'])
     workflows+=1
     if variant!=VARIANTS[-1]:r=engine.action(r,'probe')
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'PASS','case_count':len(BANK),
  'areas':dict(Counter(p['artifacts']['area'] for p in BANK)),'domains':dict(Counter(p['domain'] for p in BANK)),
  'levels':dict(Counter(p['difficulty']['level'] for p in BANK)),
  'objective_reference_combinations':objectives,'rejected_single_fact_mutants':mutants,'mode_variant_workflows':workflows,
  'diagnosis_cases':sum(p['artifacts']['diagnosis_task'] for p in BANK),'multi_policy_cases':sum(len(p['evaluation_rules']['policies'])>1 for p in BANK),
  'scope':'Contract/disclosure/fixture agreement and objective execution. Semantic judgment is intentionally unassessed by this validator; trusted tutor evidence is tested separately. Temporary profiles only.',
  'cases':definitions}
 return report

if __name__=='__main__':
 report=validate();path=ROOT/'docs/business-reasoning-validation.json';path.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
