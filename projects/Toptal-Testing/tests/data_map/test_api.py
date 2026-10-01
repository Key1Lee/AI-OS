import json
import sqlite3

import pytest

from data_system_map.repository import MetadataStore
from trainer.data_map.store import InvestigationStore

BASE='/api/map'
SYSTEM=BASE+'/systems/commerce-demo'
FAIL='model.commerce.fct_orders'
SUSPECT='model.commerce.int_order_items'


def begin(client,mode='assessment'):
    result=client.post(BASE+'/investigations',json={'system_id':'commerce-demo','mode':mode})
    assert result.status_code==201,result.text
    return result.json()


def answer(request='diagnosis-request-0001'):
    return {'request_id':request,'observed_failure':FAIL,'suspected_origin':SUSPECT,'grain':'one_row_per_order',
            'affected_outputs':['exposure.commerce.executive_dashboard','metric.commerce.daily_revenue'],
            'fix_proposal':'Preaggregate the item input to the order grain before joining.',
            'verification_plan':'Check row count, uniqueness, reconciliation and the affected reports.'}


def test_learning_inspections_and_full_durable_scenario(map_client):
    client,app=map_client();session=begin(client,'learning')
    assert not session['independent']
    for target,suffix in [(FAIL,'upstream'),(SUSPECT,'schema'),(FAIL,'tests'),(SUSPECT,'sql'),(FAIL,'impact')]:
        assert client.get(SYSTEM+'/nodes/'+target+'/'+suffix).status_code==200
    evidence=client.get(SYSTEM+'/incidents/'+FAIL).json()
    assert evidence['first_suspicious_node']==SUSPECT
    hypothesis=client.post(BASE+'/investigations/'+session['id']+'/hypotheses',json={'text':'An item join may duplicate order-level amounts.'}).json()
    assert hypothesis['actions'][-1]['kind']=='hypothesis'
    response=client.post(BASE+'/investigations/'+session['id']+'/submit',json=answer())
    assert response.status_code==200,response.text
    completed=response.json()
    assert completed['result']['score']==8 and completed['result']['total']==8
    assert not completed['result']['independent']
    assert completed['result']['tests_executed']==0 and not completed['result']['verification_performed']
    assert 'Fix validity' in completed['result']['unassessed']
    assert client.post(BASE+'/investigations/'+session['id']+'/submit',json=answer()).json()==completed
    assert client.post(BASE+'/investigations/'+session['id']+'/submit',json=answer('different-request-0002')).status_code==409
    restarted,_=map_client(path=app.state.store.path)
    assert restarted.get(BASE+'/investigations/'+session['id']).json()==completed
    assert restarted.get('/api/dashboard').json()['stats']['attempts']==0


def test_assessment_does_not_automatically_reveal_origin_on_any_route(map_client,artifacts):
    client,_=map_client();session=begin(client)
    assert session['independent']
    responses=[client.get(SYSTEM+'/graph').json(),client.get(SYSTEM+'/graph?level=models&focus='+FAIL).json(),
               client.get(SYSTEM+'/incidents/'+FAIL).json(),
               client.post(BASE+'/debug/investigate',json={'system_id':'commerce-demo','node_id':FAIL}).json(),
               client.post(SYSTEM+'/query',json={'operation':'failed_path','node_id':FAIL}).json()]
    for response in responses:
        assert 'first_suspicious_node' not in response and 'last_known_good' not in response
        assert 'next_step' not in response and 'observations' not in response
        assert 'first_bad_node' not in response
    models=responses[1]['nodes']
    assert next(n for n in models if n['id']==SUSPECT)['status']=='HEALTHY'
    assert client.get(SYSTEM+'/explain?mode=learning').status_code==409
    assert client.post(BASE+'/investigations',json={'system_id':'commerce-demo','mode':'learning'}).status_code==409
    assert client.post(BASE+'/systems/import',json={'system_id':'another','name':'Another','manifest':artifacts['manifest.json']}).status_code==409
    # The candidate may explicitly inspect legitimate node measurements, without
    # an automatic origin designation or hidden author answer.
    detail=client.get(SYSTEM+'/nodes/'+SUSPECT).json()
    assert detail['observations'][0]['actual']==2
    assert 'sql' not in detail and 'first_suspicious_node' not in detail
    assert client.get(BASE+'/investigations/current').json()['mode']=='assessment'


def test_explicit_end_and_learning_exposure_disqualifies_repeat(map_client):
    client,_=map_client();session=begin(client)
    learned=client.post(BASE+'/investigations/'+session['id']+'/end',json={'learn':True}).json()
    assert learned['mode']=='learning'
    assert client.get(BASE+'/investigations/'+session['id']).json()['status']=='abandoned'
    assert client.get(SYSTEM+'/incidents/'+FAIL).json()['first_suspicious_node']==SUSPECT
    repeated=begin(client)
    assert not repeated['independent']


def test_drafts_hypotheses_and_transition_conflicts_survive_restart(map_client):
    client,app=map_client();session=begin(client)
    endpoint=BASE+'/investigations/'+session['id']
    draft={key:value for key,value in answer().items() if key!='request_id'}
    assert client.put(endpoint+'/draft',json={**draft,'revision':0}).json()['revision']==1
    assert client.put(endpoint+'/draft',json={**draft,'revision':0}).status_code==409
    restarted,_=map_client(path=app.state.store.path)
    assert restarted.get(BASE+'/investigations/current').json()['draft']['fix_proposal']==draft['fix_proposal']
    assert restarted.post(endpoint+'/hypotheses',json={'text':'Check the order grain.'}).status_code==200
    assert restarted.post(endpoint+'/submit',json=answer()).status_code==200
    assert restarted.put(endpoint+'/draft',json={**draft,'revision':1}).status_code==409
    assert restarted.post(endpoint+'/hypotheses',json={'text':'Too late.'}).status_code==409


def test_api_operations_missing_ids_and_honest_lineage(map_client):
    client,_=map_client();begin(client)
    upstream=client.get(SYSTEM+'/nodes/'+FAIL+'/upstream').json()
    assert upstream['direct'][0]['id']==SUSPECT and len(upstream['transitive'])==4
    paths=client.post(SYSTEM+'/query',json={'operation':'shortest_path','start':'model.commerce.stg_orders','end':'exposure.commerce.executive_dashboard'}).json()
    assert paths['path']==['model.commerce.stg_orders',SUSPECT,FAIL,'model.commerce.mart_revenue','exposure.commerce.executive_dashboard']
    assert client.get(SYSTEM+'/nodes/'+FAIL+'/columns/order_id/lineage').json()['status']=='unavailable'
    assert client.get(SYSTEM+'/nodes/does-not-exist').status_code==404
    assert client.post(SYSTEM+'/query',json={'operation':'shortest_path'}).status_code==422
    assert client.get(SYSTEM+'/incidents/model.commerce.stg_orders').status_code==422


def test_import_failure_limits_and_errors_do_not_expose_values(map_client,artifacts):
    client,_=map_client()
    payload={'system_id':'uploaded','name':'Uploaded','manifest':artifacts['manifest.json']}
    valid=client.post(BASE+'/systems/import',json=payload)
    assert valid.status_code==201,valid.text
    before=client.get(BASE+'/systems/uploaded/graph').json()['snapshot_id']
    payload['manifest']={'nodes':'secret-SENTINEL-credentials'}
    failed=client.post(BASE+'/systems/import',json=payload)
    assert failed.status_code==422 and 'SENTINEL' not in failed.text
    assert client.get(BASE+'/systems/uploaded/graph').json()['snapshot_id']==before
    response=client.post(BASE+'/systems/import',json={**payload,'manifest':'secret-SENTINEL'})
    assert response.status_code==422 and 'SENTINEL' not in response.text
    assert client.post(BASE+'/systems/import',content='x'*(8*1024*1024+1)).status_code==413
    assert client.post(BASE+'/systems/import',json=payload,headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post(BASE+'/systems/import',json=payload,headers={'X-Trainer-Token':''}).status_code==403


@pytest.mark.parametrize('store',[MetadataStore,InvestigationStore])
def test_profiles_reject_other_application_database_without_changes(tmp_path,store):
    path=tmp_path/'other.db'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE learner_evidence(value TEXT)')
        connection.execute("INSERT INTO learner_evidence VALUES('preserve this')")
    before=path.read_bytes()
    with pytest.raises(ValueError):store(path)
    assert path.read_bytes()==before


def test_engine_and_trainer_adapter_boundaries():
    from pathlib import Path
    engine='\n'.join(p.read_text() for p in Path('data_system_map').rglob('*.py'))
    consumer='\n'.join(p.read_text() for p in Path('trainer/data_map').glob('*.py'))
    assert 'from trainer' not in engine and 'import trainer' not in engine
    assert 'data_system_map.adapters' not in consumer and 'sqlglot' not in consumer.lower()
