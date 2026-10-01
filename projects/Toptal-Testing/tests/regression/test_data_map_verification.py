"""Adversarial cases independently identified by the verification agent."""
import pytest
import asyncio

from data_system_map.adapters.dbt import DbtAdapter
from data_system_map.repository import MetadataStore
from data_system_map.service import DataSystemService
from tests.data_map.conftest import artifacts, map_client


@pytest.mark.parametrize('field,value', [('resource_type', []), ('resource_type', {}), ('layer', []), ('layer', {})])
def test_malformed_resource_fields_are_safe_and_atomic(map_client, artifacts, field, value):
    client, _ = map_client()
    url = '/api/map/systems/import'
    payload = {'system_id': 'adversarial', 'name': 'Adversarial', 'manifest': artifacts['manifest.json']}
    assert client.post(url, json=payload).status_code == 201
    before = client.get('/api/map/systems/adversarial/graph').json()['snapshot_id']
    raw = payload['manifest']['nodes']['model.commerce.fct_orders']
    (raw['meta'] if field == 'layer' else raw)[field] = value
    assert client.post(url, json=payload).status_code == 422
    assert client.get('/api/map/systems/adversarial/graph').json()['snapshot_id'] == before


def test_secret_patterns_in_all_imported_text_are_not_persisted(map_client, artifacts):
    client, app = map_client()
    raw = artifacts['manifest.json']['nodes']['model.commerce.fct_orders']
    raw['meta']['primary_keys'] = ['api_key=SENTINEL_PRIMARY_KEY']
    observation = raw['meta']['data_system_map']['observations'][0]
    observation.update(expected='password=SENTINEL_EXPECTED', actual='password=SENTINEL_OBSERVATION')
    payload = {'system_id': 'redacted', 'name': 'api_key=SENTINEL_SYSTEM_NAME', 'manifest': artifacts['manifest.json']}
    assert client.post('/api/map/systems/import', json=payload).status_code == 201
    response = client.get('/api/map/systems/redacted/nodes/model.commerce.fct_orders').text
    assert 'SENTINEL' not in response
    encoded = app.state.data_map.engine.snapshot('redacted').model_dump_json()
    assert 'SENTINEL' not in encoded
    # Redaction must not create comparable "good" checks from secret values.
    assert all(o.expected is None and o.actual is None for o in app.state.data_map.engine.snapshot('redacted').observations if o.node_id == raw['unique_id'])


def many_parents():
    parents = {f'source.demo.p{i:02}': {'name': f'p{i:02}', 'resource_type': 'source'} for i in range(20)}
    focus = 'model.demo.mart_focus'
    return focus, {'sources': parents, 'nodes': {focus: {'name': 'mart_focus', 'resource_type': 'model', 'depends_on': {'nodes': list(parents)}}}}


def test_secret_in_provenance_column_key_is_rejected_atomically(map_client, artifacts):
    client, app = map_client()
    payload = {'system_id': 'pointer-check', 'name': 'Pointer check', 'manifest': artifacts['manifest.json']}
    assert client.post('/api/map/systems/import', json=payload).status_code == 201
    before = app.state.data_map.engine.snapshot('pointer-check').model_dump_json()
    raw = artifacts['manifest.json']['nodes']['model.commerce.fct_orders']
    raw['columns']['password=SENTINEL_COLUMN_POINTER'] = {'name': 'safe_column'}
    response = client.post('/api/map/systems/import', json=payload)
    assert response.status_code == 422 and 'SENTINEL' not in response.text
    assert app.state.data_map.engine.snapshot('pointer-check').model_dump_json() == before


def test_large_focus_and_incident_keep_selected_node(tmp_path):
    key, manifest = many_parents()
    engine = DataSystemService(MetadataStore(tmp_path / 'metadata.db'))
    engine.import_dbt('large', 'Large', manifest, run_results={'args': {'which': 'run'}, 'results': [{'unique_id': key, 'status': 'error', 'message': 'Runtime failure'}]})
    for view in [engine.graph('large', level='models', focus=key), engine.investigate('large', key)['failure_path']]:
        assert key in {n['id'] for n in view['nodes']}
        assert len(view['nodes']) == 14 and view['truncated'] is True
        assert all(e['from_node'] in {n['id'] for n in view['nodes']} and e['to_node'] in {n['id'] for n in view['nodes']} for e in view['edges'])


@pytest.mark.parametrize('operation', ['compile', 'run', 'unknown-operation'])
def test_execution_failure_is_visible_with_evidence_and_neutral_guidance(tmp_path, operation):
    key = 'model.demo.single'
    engine = DataSystemService(MetadataStore(tmp_path / 'metadata.db'))
    engine.import_dbt('single', 'Single', {'nodes': {key: {'name': 'single', 'resource_type': 'model', 'raw_code': 'SELECT 1'}}},
                      run_results={'args': {'which': operation}, 'results': [{'unique_id': key, 'status': 'error', 'message': 'Compilation or runtime error'}]})
    assert engine.snapshot('single').nodes[0].status == 'FAILED'
    assert engine.incidents('single')[0]['node_id'] == key
    incident = engine.investigate('single', key, reveal_diagnostics=True)
    assert incident['execution_evidence'][0]['error'] == 'Compilation or runtime error'
    assert incident['execution_evidence'][0]['provenance']['source'] == 'run_results.json'
    assert 'join' not in incident['next_step'].lower()


def test_chunked_upload_is_bounded_after_authorization(map_client):
    client, app = map_client()
    token = client.headers['X-Trainer-Token']
    async def request(authenticated):
        calls, sent = [], []
        chunks = iter([b'x' * (1024 * 1024)] * 12)
        async def receive():
            calls.append(True)
            return {'type': 'http.request', 'body': next(chunks), 'more_body': True}
        async def send(message):
            sent.append(message)
        headers = [(b'host', b'testserver'), (b'content-type', b'application/json')]
        if authenticated:
            headers.append((b'x-trainer-token', token.encode()))
        await app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST','scheme':'http',
                   'path':'/api/map/systems/import','raw_path':b'/api/map/systems/import','query_string':b'',
                   'headers':headers,'client':('127.0.0.1',1234),'server':('testserver',80)}, receive, send)
        return calls, next(m['status'] for m in sent if m['type']=='http.response.start')
    calls, status = asyncio.run(request(False))
    assert status == 403 and calls == []
    calls, status = asyncio.run(request(True))
    assert status == 413 and len(calls) == 9
    assert not hasattr(app.state, 'data_map')


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


@pytest.mark.parametrize('artifact', ['manifest','run_results','freshness'])
def test_malformed_timestamps_reject_import_without_breaking_date_rendering(map_client, artifacts, artifact):
    client, _ = map_client()
    payload={'system_id':'timestamps','name':'Timestamps','manifest':artifacts['manifest.json'],
             'run_results':artifacts['run_results.json'],'freshness':artifacts['sources.json']}
    assert client.post('/api/map/systems/import',json=payload).status_code == 201
    before=client.get('/api/map/systems/timestamps/graph').json()['snapshot_id']
    if artifact=='manifest':
        payload['manifest']['metadata']['generated_at']='not-a-date'
    elif artifact=='run_results':
        payload['run_results']['results'][0]['timing']=[{'completed_at':'not-a-date'}]
    else:
        payload['freshness']['results'][0]['snapshotted_at']='not-a-date'
    assert client.post('/api/map/systems/import',json=payload).status_code == 422
    assert client.get('/api/map/systems/timestamps/graph').json()['snapshot_id'] == before
