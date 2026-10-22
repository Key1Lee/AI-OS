"""SQL Step 2 acceptance probes over the existing Step 1 engine."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from lab.problems import PROBLEMS,PROBLEM_MAP,REPRESENTATIVE_IDS
from lab.sql_lab.catalog import CATALOG
from lab.sql_lab.datasets import fixture,DOMAINS
from lab.sql_lab.postgres import Postgres,SQLRejected,parse_submission
from lab.sql_lab.evaluator import compare
from lab.sql_lab.oracles import expected
from lab.store import StateError

BANK=[p for p in PROBLEMS if p['kind'] in ('sql','debug') and p['problem_id'] not in REPRESENTATIVE_IDS]


def prepare_new(engine,pid,mode='LEARN'):
    p=PROBLEM_MAP[pid];c=CATALOG[pid];r=engine.start(pid,mode)
    observation={'prediction':'Trace row meaning and the business population before calculating.'}
    if p['artifacts'].get('prediction_sql'):
        observation['prediction_rows']=engine.postgres.execute(p['artifacts']['prediction_sql'],c,fixture(c.domain))['rows']
    r=engine.action(r,'predict',observation)
    a={'requirements':'Use stated population, time window, exclusions and unknown-value meaning.',
       'proposal':'Identify entities and their row meaning. Filter by the stated business rules. Align measures to output grain and validate with source totals.',
       'input_grain':'The documented entity or received-event grain for each source.',
       'output_grain':p['expected_output_grain'],'inputs':{t:list(DOMAINS[c.domain].table(t).primary_key) for t in c.inputs},'output_key':list(c.output_key),
       'joins':{pair:{'left_grain':DOMAINS[c.domain].table(pair.split(':')[0]).grain,'right_grain':DOMAINS[c.domain].table(pair.split(':')[1]).grain,
               'relationship':rel,'output_grain':c.output_grain} for pair,rel in c.joins.items()},
       'window':{'partition':'The business entity per requirement.','order':'Business event time and the specified stable identity.','frame':'The explicitly required current/previous or full partition frame.'},
       'duplicate_identity':'Use the stated logical business key, distinct from delivery identity.'}
    return engine.action(r,'prepare',a)


@pytest.mark.parametrize('p',BANK,ids=lambda p:p['problem_id'])
def test_every_reference_loads_and_matches_four_independent_oracles(p):
    c=CATALOG[p['problem_id']];pg=Postgres()
    for variant,seed in [('clean',1),('adversarial',1),('adversarial',2),('recall',3)]:
        data=fixture(c.domain,variant,seed)
        result=compare(pg.execute(c.solution,c,data),expected(c.oracle,data),c)
        assert result['matches'],(p['problem_id'],variant,seed,result)


def test_sample_hidden_variants_are_independent_and_pinned():
    from lab.sql_lab.contracts import fingerprint
    for p in BANK:
        c=CATALOG[p['problem_id']]
        assert len(p['hidden_tests'])==4
        assert fingerprint(fixture(c.domain,'clean'))!=fingerprint(fixture(c.domain,'adversarial'))
        for case in p['hidden_tests']:
            data=fixture(c.domain,case['fixture'],case['seed'])
            assert case['fixture_sha256']==fingerprint(data)
            assert case['oracle_sha256']==fingerprint(expected(c.oracle,data))


def test_business_sentinels_distinguish_absent_null_zero_and_boundaries():
    result={r['loan_id']:r for r in expected('bank:SQL-XFR-001',fixture('lending','clean'))}
    assert result['L1']['state']=='known' and result['L1']['known_cents']==10000
    assert result['L2']['state']=='unknown' and result['L2']['payment_rows']==1
    assert result['L3']['state']=='no_records' and result['L3']['payment_rows']==0
    assert result['L4']['state']=='zero' and result['L4']['known_rows']==1
    local=expected('bank:SQL-DATE-004',fixture('healthcare','adversarial'))
    assert next(r for r in local if r['local_day']=='2026-11-01' and r['local_hour']==1)['appointments']==2
    days=expected('bank:SQL-DATE-008',fixture('insurance','adversarial'))
    assert next(r for r in days if r['policy_id']=='P4')['coverage_days']==2


def test_identifier_text_is_not_coerced_and_order_is_checked():
    c=CATALOG['SQL-FND-008'];data=fixture(c.domain);actual=Postgres().execute(c.solution,c,data)
    ref=expected(c.oracle,data);assert compare(actual,ref,c)['matches']
    actual['rows'][0]['external_code']='123'
    assert not compare(actual,ref,c)['matches']
    c=CATALOG['SQL-FND-010'];data=fixture(c.domain);actual=Postgres().execute(c.solution,c,data)
    actual['rows'].reverse();assert not compare(actual,expected(c.oracle,data),c)['matches']


def test_join_and_window_reasoning_are_mandatory(engine):
    r=engine.start('SQL-WIN-003');r=engine.action(r,'predict',{'prediction':'A seller is the ranked entity.'})
    p=PROBLEM_MAP[r['problem_id']];c=CATALOG[r['problem_id']]
    base={'requirements':'Rank per region with stable ties.','proposal':'Aggregate then order each region.',
          'input_grain':'seller and purchase','output_grain':p['expected_output_grain'],
          'inputs':{t:list(DOMAINS[c.domain].table(t).primary_key) for t in c.inputs},'output_key':list(c.output_key)}
    with pytest.raises(StateError,match='left/right'):engine.action(r,'prepare',base)
    base['joins']={'sellers:purchases':{'left_grain':'seller','right_grain':'purchase','relationship':'1:M','output_grain':'seller'}}
    with pytest.raises(StateError,match='partition'):engine.action(r,'prepare',base)


def test_debug_diagnosis_precedes_fix_and_is_preserved(engine):
    r=engine.start('SQL-JOIN-005','DEBUG');v=engine.view(r)
    assert v['broken_output']['rows'] and v['learning_step']==0
    with pytest.raises(StateError):engine.action(r,'submit',{'sql':PROBLEM_MAP[r['problem_id']]['solution'],'reason':'Repair'})
    r=prepare_new(engine,'SQL-JOIN-005','DEBUG')
    r=engine.action(r,'submit',{'sql':PROBLEM_MAP[r['problem_id']]['solution'],'reason':'Each independent child must contribute once.'})
    assert r['attempts'][-1]['status']=='PASS'
    assert r['answers']['prediction']


def test_review_and_performance_do_not_autocertify_prose(engine):
    r=prepare_new(engine,'SQL-ADV-006','PERFORMANCE');p=PROBLEM_MAP[r['problem_id']]
    with pytest.raises(StateError,match='assessment'):engine.action(r,'submit',{'sql':p['solution'],'reason':'A bounded predicate.'})
    r=engine.action(r,'submit',{'sql':p['solution'],'reason':'Use the explicit UTC boundaries.',
      'assessment':'Scan only eligible partitions if the physical partition key matches; verify the warehouse plan. Local fixture cost does not prove production cost.'})
    a=r['attempts'][-1];assert a['status']=='REVIEW_REQUIRED' and a['evaluation']['objective_status']=='PASS'
    assert a['evaluation']['query_plan']['plan'][0]['Plan']
    assert engine.mastery.state(p['mastery_tags'][0])['correct_attempts']==0
    r=engine.review(r['run_id'],a['attempt_id'],'Tutor','Bounded filters, grain and plan limits reviewed.',
       {criterion:True for criterion in a['evaluation']['criteria']},p['mastery_tags'])
    assert r['attempts'][-1]['status']=='PASS'


def test_error_taxonomy_and_retry_evidence_persist(engine):
    r=prepare_new(engine,'SQL-XFR-001')
    r=engine.action(r,'submit',{'sql':'SELECT loan_id, FROM loans WHERE','reason':'Attempt the projection.'})
    a=r['attempts'][-1];assert a['status']=='FAIL' and a['evaluation']['error_classes']
    tag=PROBLEM_MAP[r['problem_id']]['mastery_tags'][0]
    assert engine.mastery.state(tag)['error_classes']


def test_changed_requirement_is_an_explicit_followup(engine):
    r=prepare_new(engine,'SQL-GRN-003');p=PROBLEM_MAP[r['problem_id']]
    with pytest.raises(StateError):engine.action(r,'next_stage')
    r=engine.action(r,'submit',{'sql':p['solution'],'reason':'Each item contributes once.'})
    r=engine.action(r,'finish',{'connection':'Reconcile source line totals at order grain.'})
    assert engine.view(r)['next_stage']=='SQL-JOIN-006'
    later=engine.action(r,'next_stage');assert later['problem_id']=='SQL-JOIN-006' and later['run_id']!=r['run_id']


def test_prediction_runs_against_sample_before_construction(engine):
    r=engine.start('SQL-AGG-001');p=PROBLEM_MAP[r['problem_id']]
    with pytest.raises(StateError,match='JSON'):engine.action(r,'predict',{'prediction':'Count known ratings.'})
    r=engine.action(r,'predict',{'prediction':'Unknown scores are excluded only from the rating count.',
          'prediction_rows':[{'tickets':3,'rated':2}]})
    assert r['answers']['output_prediction']['matches']


def test_equivalent_query_passes_without_unearned_named_technique_evidence(engine):
    r=prepare_new(engine,'SQL-DED-002')
    query="WITH p AS (SELECT DISTINCT ON(transfer_id) * FROM wallet_events ORDER BY transfer_id,event_at DESC,event_id DESC) SELECT transfer_id,wallet_id,cents FROM p WHERE status='posted'"
    r=engine.action(r,'submit',{'sql':query,'reason':'The latest logical state is selected before testing posted.'})
    assert r['attempts'][-1]['status']=='PASS'
    assert engine.mastery.state('sql.windows.row_number')['gaps']['application']
    assert not engine.mastery.state('sql.deduplication.latest_version')['gaps']['application']


def test_native_source_join_evidence_uses_declared_business_identity(monkeypatch):
    from lab.sql_lab import integrations
    monkeypatch.setattr(integrations,'invoke',lambda system,payload,**kw:payload)
    for pid,pair,key in [('SQL-JOIN-007',('attempts','captures'),'payment_id'),('SQL-CTE-010',('conversions','touches'),'user_id'),('SQL-XFR-009',('scheduled_payments','payments'),'schedule_id')]:
        c=CATALOG[pid];data=fixture(c.domain)
        payload=integrations.modeling(c,data,{'columns':list(c.output),'rows':expected(c.oracle,data)})
        join=next(j for j in payload['joins'] if (j['left_table'],j['right_table'])==pair)
        assert join['left_key']==join['right_key']==key


def test_calendar_comparisons_and_optional_funnel_have_business_sentinels():
    from decimal import Decimal
    weekly=expected('bank:SQL-XFR-014',fixture('advertising','adversarial'))
    assert next(r for r in weekly if r['campaign_id']=='K1' and r['week']=='2026-10-12')['wow_rate']==Decimal('-1.00')
    assert next(r for r in weekly if r['campaign_id']=='K2' and r['week']=='2026-10-12')['prior_clicks'] is None
    annual=expected('bank:SQL-XFR-015',fixture('retail','adversarial'))
    assert next(r for r in annual if r['store_id']=='S1' and r['month']=='2026-11-01')['yoy_rate']==Decimal('-0.50')
    data=fixture('commerce','adversarial')
    required={r['customer_id']:r for r in expected('bank:SQL-PAT-001',data)}
    optional={r['customer_id']:r for r in expected('bank:SQL-XFR-016',data)}
    assert required['C4']['converted']==0 and optional['C4']['converted']==1
    assert optional['C3']['eligible']==0 # Its only view predates signup.
