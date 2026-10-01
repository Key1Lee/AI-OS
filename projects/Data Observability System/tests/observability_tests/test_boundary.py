"""Independent distribution, ownership and stable public graph contract."""
import ast
import subprocess
import sys
from pathlib import Path
import data_system_map
from data_system_map import create_service
from data_system_map.contracts import GraphSnapshot


def test_distribution_has_no_consumer_imports_or_cycle():
    root=Path(data_system_map.__file__).parent
    edges={}
    for path in root.rglob('*.py'):
        name='data_system_map.'+'.'.join(path.relative_to(root).with_suffix('').parts)
        edges[name]=set()
        for node in ast.walk(ast.parse(path.read_text())):
            imports=([alias.name for alias in node.names] if isinstance(node,ast.Import) else
                     [node.module or ''] if isinstance(node,ast.ImportFrom) else [])
            assert not any(i.split('.')[0] in {'trainer','apps','app','tests'} for i in imports),path
            edges[name].update(i for i in imports if i.startswith('data_system_map.'))
    def visit(name,stack):
        assert name not in stack,stack+[name]
        for dep in edges.get(name,()):visit(dep,stack+[name])
    for name in edges:visit(name,[])


def test_installed_package_and_demo_work_outside_checkout(tmp_path):
    script="from pathlib import Path; from data_system_map import create_service; e=create_service(Path('metadata.db'),seed_demo=True); assert len(e.snapshot('commerce-demo').nodes)==11"
    result=subprocess.run([sys.executable,'-c',script],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_independent_api_contract_and_sample_flow(map_client):
    client,app=map_client()
    assert client.get('/api/map/investigations/current').status_code==404
    assert not any('investigations' in path for path in client.get('/api/openapi.json').json()['paths'])
    prefix='/api/map/systems/commerce-demo'
    overview=client.get(prefix+'/graph').json()
    assert overview['contract_version']=='data-map-v1' and len(overview['stages'])==5 and overview['nodes']==[]
    engine=app.state.data_map.engine
    snapshot=GraphSnapshot.model_validate_json(engine.snapshot('commerce-demo').model_dump_json())
    assert snapshot.system_id=='commerce-demo' and len(snapshot.nodes)==11
    fail='model.commerce.fct_orders'
    response=client.get(prefix+'/incidents/'+fail).json()
    assert response['first_suspicious_node']=='model.commerce.int_order_items'
    assert response['last_known_good']==['model.commerce.stg_orders']
    assert response['first_bad_node'] is None
    assert {n['id'] for n in response['impact']['affected_outputs']}=={'metric.commerce.daily_revenue','exposure.commerce.executive_dashboard'}
    path=client.post(prefix+'/query',json={'operation':'shortest_path','start':'source.commerce.shopify.raw_orders','end':'exposure.commerce.executive_dashboard'}).json()['path']
    assert path==['source.commerce.shopify.raw_orders','model.commerce.stg_orders','model.commerce.int_order_items',fail,'model.commerce.mart_revenue','exposure.commerce.executive_dashboard']
    assert client.get(prefix+'/nodes/'+fail+'/sql').json()['executed'] is False
    assert client.get(prefix+'/nodes/'+fail+'/columns/order_id/lineage').json()['status']=='unavailable'
    assert client.get(prefix+'/explain').json()['provider']=='deterministic'
