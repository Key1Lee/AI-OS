"""The trainer consumes one public package and applies its disclosure policy."""
import ast
import os
from pathlib import Path
import pytest
from data_system_map import GraphSnapshot
from data_system_map.api.contracts import GraphQuery
from apps.api.data_map import Runtime
from trainer.config import ROOT,Settings


def test_trainer_uses_public_facade_only():
    source=ROOT/'apps/api/data_map.py'
    consumers=[source,* (ROOT/'trainer/data_map').glob('*.py')]
    for path in consumers:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.ImportFrom) and (node.module or '').startswith('data_system_map'):
                assert node.module not in {'data_system_map.graph','data_system_map.repository','data_system_map.service','data_system_map.adapters.dbt','data_system_map.security'},path


def test_public_contract_and_trainer_projection_are_distinct(map_client):
    client,app=map_client()
    client.get('/api/map/systems')
    engine=app.state.data_map.engine
    snapshot=engine.snapshot('commerce-demo')
    assert isinstance(snapshot,GraphSnapshot)
    fail='model.commerce.fct_orders'
    raw=engine.investigate('commerce-demo',fail,reveal_diagnostics=True)
    assert raw['first_suspicious_node']=='model.commerce.int_order_items'
    session=client.post('/api/map/investigations',json={'system_id':'commerce-demo','mode':'assessment'}).json()
    prefix='/api/map/systems/commerce-demo'
    for payload in [{'operation':'failed_path','node_id':fail}]:
        GraphQuery.model_validate(payload)
        result=client.post(prefix+'/query?mode=learning&reveal_diagnostics=true',json=payload).json()
        assert 'first_suspicious_node' not in result and 'next_step' not in result
        assert result['message'].startswith('Assessment-safe')
    result=client.get(prefix+'/graph?level=models&mode=learning&reveal_diagnostics=true').json()
    assert result['snapshot_id']==session['snapshot_id'] and result['audience']=='assessment'
    assert next(n for n in result['nodes'] if n['id']=='model.commerce.int_order_items')['status']=='HEALTHY'
    assert client.get(prefix+'/explain').status_code==409
    assert client.post('/api/map/investigations/'+session['id']+'/end',json={'learn':True}).status_code==200
    result=client.get(prefix+'/incidents/'+fail).json()
    assert result['first_suspicious_node']==raw['first_suspicious_node']


def test_default_profile_configuration_points_to_new_project(monkeypatch,tmp_path):
    # Inspect the factory argument without touching the learner databases.
    import apps.api.data_map as adapter
    captured=[]
    class Stop(Exception):pass
    def capture(path,**kwargs):captured.append(path);raise Stop
    monkeypatch.setattr(adapter,'create_service',capture)
    monkeypatch.delenv('OBSERVABILITY_DB',raising=False)
    with pytest.raises(Stop):Runtime(Settings())
    assert captured[-1]==ROOT.parent/'Data Observability System/data/observability.db'
    custom=tmp_path/'generic.db'
    monkeypatch.setenv('OBSERVABILITY_DB',str(custom))
    with pytest.raises(Stop):Runtime(Settings())
    assert captured[-1]==custom
    with pytest.raises(Stop):Runtime(Settings(database_path=tmp_path/'isolated.db'))
    assert captured[-1]==tmp_path/'data-map-isolated.db'
