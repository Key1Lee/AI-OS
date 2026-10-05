"""Trainer policy regressions identified during independent verification."""
import pytest
from tests.data_map.conftest import map_client


def test_imported_system_without_rubric_rejects_grading_safely(map_client):
    client, _ = map_client()
    key = 'model.demo.single'
    assert client.post('/api/map/systems/import', json={'system_id':'no-rubric','name':'No rubric','manifest':{'nodes':{key:{'name':'single','resource_type':'model'}}}}).status_code == 201
    session = client.post('/api/map/investigations',json={'system_id':'no-rubric','mode':'learning'}).json()
    response = client.post('/api/map/investigations/'+session['id']+'/submit',json={'request_id':'ungraded-1','observed_failure':key,'suspected_origin':key,'grain':'unknown','affected_outputs':[],'fix_proposal':'','verification_plan':'','notes':''})
    assert response.status_code == 409 and 'no authored grading contract' in response.text
    assert client.get('/api/map/investigations/current').json()['id'] == session['id']


@pytest.mark.parametrize('field,value', [('observed_failure','password=SENTINEL_DRAFT'),('suspected_origin','api_key=SENTINEL_DRAFT'),('affected_outputs',['sk-SENTINEL_DRAFTSECRET'])])
def test_sensitive_draft_selection_strings_are_rejected_before_storage(map_client, field, value):
    client, _ = map_client()
    session=client.post('/api/map/investigations',json={'system_id':'commerce-demo','mode':'learning'}).json()
    response=client.put('/api/map/investigations/'+session['id']+'/draft',json={'revision':0,field:value})
    assert response.status_code == 422 and 'SENTINEL' not in response.text
    assert 'SENTINEL' not in client.get('/api/map/investigations/'+session['id']).text
