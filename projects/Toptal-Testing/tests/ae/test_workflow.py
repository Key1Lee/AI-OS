from datetime import datetime,timedelta,timezone

from sqlalchemy import select

from trainer.execution.sql import ExecutionUnavailable,SqlRunner
from trainer.config import Settings
from trainer.repositories.models import EventRow,ExerciseVersionRow,SubmissionRow


def start(client,exercise='sql-order-reconciliation',mode='practice'):
    response=client.post('/api/attempts',json={'mode':mode,'exercise_id':exercise})
    assert response.status_code==201,response.text
    return response.json()


def submit(client,attempt,code,request='request-0001',**extra):
    return client.post(f"/api/attempts/{attempt['id']}/submit",json={'code':code,'request_id':request,**extra})


def test_offline_vertical_loop_idempotency_and_restart(ae_factory,bank):
    client,service=ae_factory()
    attempt=start(client)
    query=bank.exercises[attempt['exercise']['id']].reference_solution
    run=client.post(f"/api/attempts/{attempt['id']}/run",json={'code':query})
    assert run.status_code==200 and run.json()['run']['ok']
    assert client.get('/api/dashboard').json()['stats']['attempts']==0
    result=submit(client,attempt,query)
    assert result.status_code==200,result.text
    assert result.json()['result']['outcome']=='Correct'
    assert result.json()['result']['independent']
    duplicate=submit(client,attempt,query)
    assert duplicate.status_code==200
    snapshot=client.get('/api/dashboard').json()
    assert snapshot['stats']['attempts']==1 and snapshot['stats']['tested']==5
    assert snapshot['recommendation']['exercise_id']!=attempt['exercise']['id']
    assert snapshot['competencies'][2]['level']==2
    restarted,_=ae_factory(path=service.store.path)
    assert restarted.get('/api/dashboard').json()['stats']==snapshot['stats']
    assert restarted.get('/api/attempts/'+attempt['id']).json()['result']==result.json()['result']


def test_failure_feedback_hides_rows_and_revision_has_no_independent_credit(ae_factory,bank):
    client,_=ae_factory()
    attempt=start(client)
    query="SELECT o.order_id,COALESCE(SUM(p.amount),0) AS paid_total,COALESCE(SUM(i.units),0) AS unit_total FROM orders o LEFT JOIN payments p USING(order_id) LEFT JOIN items i USING(order_id) WHERE status='completed' GROUP BY o.order_id"
    response=submit(client,attempt,query)
    assert response.status_code==200
    result=response.json()['result']
    assert result['outcome']!='Correct'
    assert any(not c['passed'] and c['hidden'] for c in result['categories'])
    assert all(not {'rows','expected_rows','tables','code'}&set(c) for c in result['categories'])
    assert client.get('/api/mistakes').json()
    revision=client.post(f"/api/attempts/{attempt['id']}/revise").json()
    assert revision['parent_attempt_id']==attempt['id']
    passed=submit(client,revision,bank.exercises['sql-order-reconciliation'].reference_solution,'revision-0001').json()
    assert passed['result']['outcome']=='Correct' and not passed['result']['independent']


def test_hints_and_solution_exposure_are_sticky(ae_factory,bank):
    client,_=ae_factory()
    attempt=start(client,'sql-customer-latest')
    base=f"/api/attempts/{attempt['id']}"
    assert client.post(base+'/hints').json()['level']==1
    solution=client.post(base+'/solution').json()
    result=submit(client,attempt,solution['code']).json()
    assert not result['result']['independent'] and result['solution_seen']
    fresh=start(client,'sql-customer-latest')
    result=submit(client,fresh,solution['code'],'repeated-0001').json()
    assert not result['result']['independent']


def test_external_assistance_is_recorded(ae_factory,bank):
    client,_=ae_factory();attempt=start(client)
    response=submit(client,attempt,bank.exercises['sql-order-reconciliation'].reference_solution,external_assistance=True).json()
    assert response['external_assistance'] and not response['result']['independent']


def test_strict_mode_denies_hint_and_clarification_is_not_assistance(ae_factory,bank):
    client,_=ae_factory();attempt=start(client,mode='interview')
    base='/api/attempts/'+attempt['id']
    assert client.post(base+'/hints').json()['denied']
    assert client.post(base+'/clarifications',json={'question':'Are child IDs unique?'}).status_code==200
    result=submit(client,attempt,bank.exercises['sql-order-reconciliation'].reference_solution).json()
    assert result['hint_count']==0 and result['result']['independent']
    assert len(result['interactions'])==2


def test_pause_resume_and_draft_revision_rejects_stale_write(ae_factory):
    client,service=ae_factory();attempt=start(client)
    base='/api/attempts/'+attempt['id']
    payload={'code':'SELECT draft','explanation':'The saved assumption','revision':0}
    assert client.put(base+'/draft',json=payload).json()['revision']==1
    assert client.put(base+'/draft',json={**payload,'code':'stale text'}).status_code==409
    assert client.post(base+'/pause').json()['status']=='paused'
    assert client.post(base+'/run',json={'code':'SELECT 1'}).status_code==409
    restarted,_=ae_factory(path=service.store.path)
    resumed=restarted.post('/api/attempts',json={}).json()
    assert resumed['id']==attempt['id'] and resumed['code']=='SELECT draft'


class UnavailableRunner(SqlRunner):
    def grade(self,code,exercise):raise ExecutionUnavailable('Test infrastructure unavailable')


def test_infrastructure_failure_saves_submission_without_mastery(ae_factory,bank):
    client,service=ae_factory(runner=UnavailableRunner(Settings()))
    attempt=start(client);query=bank.exercises['sql-order-reconciliation'].reference_solution
    assert submit(client,attempt,query).status_code==503
    stored=client.get('/api/attempts/'+attempt['id']).json()
    assert stored['code']==query and stored['status']=='active'
    assert client.get('/api/dashboard').json()['stats']['attempts']==0
    with service.store.transaction() as session:
        assert session.get(SubmissionRow,'request-0001').status=='failed'
    service.runner=SqlRunner(Settings())
    assert submit(client,attempt,query).json()['result']['outcome']=='Correct'


def test_request_id_reuse_and_completed_edits_rejected(ae_factory,bank):
    client,_=ae_factory();attempt=start(client);query=bank.exercises['sql-order-reconciliation'].reference_solution
    assert submit(client,attempt,query).status_code==200
    assert submit(client,attempt,'SELECT 1').status_code==409
    assert client.put('/api/attempts/'+attempt['id']+'/draft',json={'code':'change','revision':0}).status_code==409


def test_api_rejects_cross_origin_missing_token_and_bad_host(ae_factory):
    client,_=ae_factory()
    assert client.post('/api/attempts',json={},headers={'Origin':'https://attacker.example'}).status_code==403
    assert client.post('/api/attempts',json={},headers={'X-Trainer-Token':''}).status_code==403
    assert client.get('/api/dashboard',headers={'Host':'attacker.example'}).status_code==400


def test_transfer_resolves_observed_gap_and_logs_evidence(ae_factory,bank):
    client,service=ae_factory()
    failed=start(client,'sql-customer-latest')
    assert submit(client,failed,'SELECT customer_id,email,updated_at FROM customer_updates').status_code==200
    transfer=start(client,'sql-inventory-current')
    passed=submit(client,transfer,bank.exercises['sql-inventory-current'].reference_solution,'transfer-0001').json()
    assert passed['result']['independent']
    mistakes=client.get('/api/mistakes').json()
    assert mistakes and all(m['status']=='VERIFIED_CLOSED' for m in mistakes)
    with service.store.transaction() as session:
        events=list(session.scalars(select(EventRow.event_type)))
        assert 'mistake_retested' in events and 'mastery_changed' in events


def test_version_hash_prevents_silent_history_change(ae_factory,bank):
    _,service=ae_factory()
    exercise=bank.exercises['sql-order-reconciliation']
    original=exercise.title
    try:
        exercise.title='Changed without version bump'
        try:service.store.seed(bank)
        except ValueError as error:assert 'version bump' in str(error)
        else:raise AssertionError('Mutable version was accepted')
    finally:exercise.title=original
    with service.store.transaction() as session:
        stored=session.get(ExerciseVersionRow,'sql-order-reconciliation:v1')
        assert stored.definition['title']==original


def test_new_version_does_not_change_existing_attempt(ae_factory,bank):
    client,service=ae_factory();old=start(client)
    exercise=service.bank.exercises['sql-order-reconciliation'];original=exercise.version
    try:
        exercise.version=2;service.store.seed(service.bank)
        assert client.get('/api/attempts/'+old['id']).json()['exercise']['version']==1
        new=start(client)
        assert new['exercise']['version']==2
    finally:exercise.version=original
