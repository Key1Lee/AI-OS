from copy import deepcopy
from datetime import datetime,timezone
import json
import pytest
from lab.learning_engine import LearningEngine
from lab.problems import PROBLEM_MAP
from lab.store import Store,StateError
from lab.sql_lab.postgres import Postgres,SQLRejected,parse_submission
from lab.sql_lab.catalog import CATALOG
from lab.sql_lab.datasets import fixture,DOMAINS
from lab.sql_lab.oracles import expected
from lab.sql_lab.evaluator import compare
from .conftest import prepared,solved


@pytest.mark.parametrize('pid',['SQL-LOAN-001','SQL-ORDER-001','SQL-INVOICE-001','MODEL-GRAIN-001','MODEL-SCD-001','DEBUG-ORDER-001'])
def test_representative_objective_solutions_run_in_real_engines(engine,pid):
    r=solved(engine,pid);a=r['attempts'][-1]
    assert a['status']=='PASS',a['evaluation'].get('integration_errors',a['evaluation'])
    v=engine.view(r)
    assert 'solution' not in v and 'hidden_tests' not in json.dumps(v)
    if 'cases' in a['evaluation']:
        assert len(a['evaluation']['cases'])==4 and all(c['matches'] for c in a['evaluation']['cases'])
        assert all('PostgreSQL' in c['actual']['execution'] for c in a['evaluation']['cases'])
        assert 'data_modeling_lab' in a['evaluation']['native']['modeling']['provenance']
        assert 'quality_system' in a['evaluation']['native']['quality']['provenance']
        assert a['evaluation']['native']['observability']['snapshot_id']
    for tag in PROBLEM_MAP[pid]['mastery_tags']:
        assert engine.mastery.state(tag)['mastery_state']=='INTRODUCED' # Explanation has not been reviewed.


def test_independent_financial_sentinel_and_non_accidental_correctness(engine):
    clean=expected('principal',fixture('fintech','clean'))
    bad=expected('principal',fixture('fintech','adversarial'))
    assert {r['loan_id']:r['total_principal_cents'] for r in clean}=={'L1':15000,'L2':7000,'L3':0,'L4':3000}
    assert {r['loan_id']:r['total_principal_cents'] for r in bad}=={'L1':30000,'L2':5000,'L3':0,'L4':3000}
    r=prepared(engine,'SQL-LOAN-001')
    query="SELECT l.loan_id,COALESCE(SUM(p.principal_cents),0) AS total_principal_cents FROM loans l LEFT JOIN payment_events p USING(loan_id) GROUP BY l.loan_id"
    r=engine.action(r,'submit',{'sql':query,'reason':'I assumed event rows represent payments.'})
    e=r['attempts'][-1]['evaluation'];assert e['cases'][0]['matches'] and not e['cases'][1]['matches']
    v=engine.view(r);assert v['status']=='FAIL' and v['submission']['sql']==query
    assert v['comparison']['actual']['rows']!=v['comparison']['expected']
    assert any(t['transaction_id']=='TX1' and t['raw_sum_cents']==20000 and t['eligible_principal_cents']==10000 for t in v['row_trace']['rows'])
    assert set(v['feedback'])=={'error','fix','why','try_again'} and len(json.dumps(v['feedback']))<700
    assert 'solution' not in v
    with pytest.raises(StateError):engine.action(r,'reveal')
    r=engine.action(r,'reveal',{'explicit_request':True});assert engine.view(r)['solution']==PROBLEM_MAP[r['problem_id']]['solution']


def test_wrong_declared_grain_fails_even_with_correct_sql(engine):
    r=prepared(engine,'SQL-LOAN-001');r['answers']['preparation']['output_key']=['transaction_id']
    r=engine.action(r,'submit',{'sql':PROBLEM_MAP[r['problem_id']]['solution'],'reason':'I declared event grain.'})
    assert r['attempts'][-1]['status']=='FAIL'
    assert 'declared' in r['attempts'][-1]['feedback']['error']


def test_debug_fanout_and_actual_original_failure(engine):
    r=engine.start('DEBUG-ORDER-001','DEBUG');p=PROBLEM_MAP[r['problem_id']]
    assert r['broken_output']['rows'] and 'expected' not in engine.view(r)
    r=prepared(engine,'DEBUG-ORDER-001','DEBUG')
    r=engine.action(r,'submit',{'sql':p['artifacts']['broken_sql'],'reason':'I joined lines to refunds.'})
    v=engine.view(r);assert v['status']=='FAIL'
    assert any(j['fanout'] and j['actual_cardinality']=='N:N' for j in v['join_evidence'])


def test_execution_error_is_exact_and_query_is_preserved(engine):
    r=prepared(engine,'SQL-LOAN-001');sql='SELECT loan_id,missing_measure AS total_principal_cents FROM loans'
    r=engine.action(r,'submit',{'sql':sql,'reason':'I need to check this column.'})
    v=engine.view(r);assert v['submission']['sql']==sql and 'missing_measure' in v['comparison']['error']['message']
    assert v['comparison']['error']['sqlstate']=='42703'


@pytest.mark.parametrize('query',[
 'DELETE FROM loans','SELECT 1; SELECT 2','SELECT * INTO stolen FROM loans',
 'WITH x AS (DELETE FROM loans RETURNING *) SELECT * FROM x',
 "SELECT pg_read_file('/etc/passwd') FROM loans",'SELECT * FROM pg_catalog.pg_authid',
 "SELECT pg_catalog.set_config('statement_timeout','0',false) FROM loans",
 'SELECT * FROM loans FOR UPDATE','WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) SELECT * FROM x',
])
def test_execution_boundary_rejects_mutations_or_system_access(query):
    with pytest.raises(SQLRejected):parse_submission(query,('loans','payment_events'))


def test_sql_solution_hidden_in_interview_until_finish(engine):
    r=solved(engine,'SQL-LOAN-001','INTERVIEW');v=engine.view(r)
    assert 'comparison' not in v and 'solution' not in v and 'skills_tested' not in v['problem']
    assert 'rubric' not in v and 'error_classes' not in v and v['feedback']['fix'] is None
    with pytest.raises(StateError):engine.action(r,'reveal',{'explicit_request':True})
    r=engine.action(r,'finish',{'connection':'Resolve identity before interpreting status or money.'})
    assert 'comparison' in engine.view(r)
    r=engine.action(r,'reveal',{'explicit_request':True});assert 'solution' in engine.view(r)


def test_architecture_requires_real_tutor_review(engine):
    r=solved(engine,'ARCH-PIPELINE-001','SYSTEM_DESIGN');a=r['attempts'][-1];p=PROBLEM_MAP[r['problem_id']]
    assert a['status']=='REVIEW_REQUIRED' and engine.mastery.state(p['mastery_tags'][0])['correct_attempts']==0
    with pytest.raises(StateError):engine.review(r['run_id'],a['attempt_id'],'Tutor','Criteria reviewed.',{'one':True},p['mastery_tags'])
    reviewed=engine.review(r['run_id'],a['attempt_id'],'Tutor','Daily source cadence cannot support the promised SLA; revised requirements and replay design are supported.',
      {c:True for c in p['evaluation_rules']['criteria']},p['mastery_tags'])
    assert reviewed['attempts'][-1]['status']=='PASS'
    assert engine.mastery.state(p['mastery_tags'][0])['mastery_state']=='APPLIED'
    with pytest.raises(StateError):engine.review(r['run_id'],a['attempt_id'],'Tutor','Again.',{c:True for c in p['evaluation_rules']['criteria']},p['mastery_tags'])


def test_hints_cannot_earn_unassisted_application(engine):
    r=prepared(engine,'SQL-INVOICE-001');r=engine.action(r,'hint')
    r=engine.action(r,'submit',{'sql':PROBLEM_MAP[r['problem_id']]['solution'],'reason':'I used the hint.'})
    tag=PROBLEM_MAP[r['problem_id']]['mastery_tags'][0]
    assert r['attempts'][-1]['status']=='PASS'
    assert engine.mastery.state(tag)['gaps']['application']


def test_progress_and_saved_attempt_survive_restart(engine):
    r=solved(engine,'SQL-INVOICE-001')
    restarted=LearningEngine(Store(engine.store.root),clock=engine.clock)
    assert restarted.view(restarted.store.get(r['run_id']))==engine.view(r)
    tag=PROBLEM_MAP[r['problem_id']]['mastery_tags'][0]
    assert restarted.mastery.state(tag)==engine.mastery.state(tag)


def test_amount_sort_cannot_accidentally_replace_event_id_tie_break(engine):
    p=PROBLEM_MAP['SQL-LOAN-001'];r=prepared(engine,p['problem_id'])
    # The first fixtures revise upward, so amount ordering looks correct.
    # A separate fixture revises downward at the same timestamp.
    bad=p['solution'].replace('event_id DESC','principal_cents DESC NULLS LAST')
    r=engine.action(r,'submit',{'sql':bad,'reason':'I selected the largest amount when times tie.'})
    cases=r['attempts'][-1]['evaluation']['cases']
    assert all(c['matches'] for c in cases[:3])
    assert not cases[3]['matches'] and r['attempts'][-1]['status']=='FAIL'


def test_hidden_fixture_and_oracle_versions_are_pinned_and_private():
    p=PROBLEM_MAP['SQL-LOAN-001'];test=p['hidden_tests'][0]
    assert len(test['fixture_versions'])==4 and len(test['oracle_versions'])==4
    assert all(len(v)==64 for v in test['fixture_versions'].values())
    from lab.problems import learner_problem
    body=json.dumps(learner_problem(p,'INTERVIEW'))
    assert 'fixture_versions' not in body and 'oracle_versions' not in body


def test_null_money_is_a_native_warning_not_silently_healthy(engine):
    r=solved(engine,'SQL-LOAN-001');v=engine.view(r)
    assert v['status']=='PASS' # The exercise explicitly defines NULL contribution as zero.
    assert any(w['dataset']=='payment_events' and w['severity']=='WARNING' and w['failed_rows']==1 for w in v['source_warnings'])
    bundle=r['attempts'][-1]['evaluation']['native']['quality']['bundles']['payment_events']
    assert any(x['severity']=='WARNING' and x['status']=='WARN' for x in bundle['events'])


@pytest.mark.parametrize('old,new',[('event_at DESC,event_id DESC','event_id DESC'),('event_at DESC','received_at DESC')])
def test_late_older_revision_does_not_win_by_arrival_or_id_alone(engine,old,new):
    p=PROBLEM_MAP['SQL-LOAN-001'];r=prepared(engine,p['problem_id'])
    wrong=p['solution'].replace(old,new)
    r=engine.action(r,'submit',{'sql':wrong,'reason':'I treated ingestion order as business event order.'})
    cases=r['attempts'][-1]['evaluation']['cases']
    assert all(c['matches'] for c in cases[:3])
    assert not cases[3]['matches'] and r['attempts'][-1]['status']=='FAIL'
