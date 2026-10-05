from sqlalchemy import select

from trainer.repositories.models import AttemptRow
from tests.ae.test_workflow import start


def test_resuming_older_draft_makes_it_the_dashboard_primary(ae_factory):
    client,_=ae_factory()
    first=start(client,'sql-order-reconciliation')
    second=start(client,'sql-price-levels')
    assert client.get('/api/dashboard').json()['active_attempt']['id']==second['id']
    assert client.post('/api/attempts/'+first['id']+'/resume').status_code==200
    assert client.get('/api/dashboard').json()['active_attempt']['id']==first['id']


def test_review_filter_does_not_resume_an_unrelated_draft(ae_factory):
    client,_=ae_factory();old=start(client,'sql-order-reconciliation')
    result=client.post('/api/attempts',json={'competency':'sql.windows'})
    assert result.status_code==201
    assert result.json()['id']!=old['id']
    assert 'sql.windows' in result.json()['exercise']['competencies']


def test_cannot_resume_other_draft_during_grading(ae_factory):
    client,service=ae_factory();first=start(client)
    second=start(client,'sql-price-levels')
    with service.store.transaction(write=True) as session:
        session.get(AttemptRow,second['id']).status='grading'
    assert client.post('/api/attempts/'+first['id']+'/resume').status_code==409
