import pytest

from data_system_map.adapters.dbt import ArtifactError,DbtAdapter
from data_system_map.repository import MetadataStore
from data_system_map.service import DataSystemService


def ingest(artifacts):
    return DbtAdapter().ingest('commerce-demo','Commerce',artifacts['manifest.json'],run_results=artifacts['run_results.json'],catalog=artifacts['catalog.json'],freshness=artifacts['sources.json'])


def test_real_generated_demo_contract_and_provenance(artifacts):
    from scripts.generate_commerce_map import generate
    assert generate()==artifacts
    graph=ingest(artifacts)
    nodes={n.id:n for n in graph.nodes}
    # Authored fixture: eight data dependencies plus two test associations.
    assert len(nodes)==11 and len(graph.edges)==10
    assert nodes['model.commerce.fct_orders'].status=='FAILED'
    assert nodes['model.commerce.int_order_items'].status=='HEALTHY'
    test=next(t for t in graph.tests if t.node_id=='model.commerce.fct_orders')
    assert test.failures==2 and test.provenance.source=='run_results.json'
    assert nodes['model.commerce.stg_orders'].primary_keys==['order_id']
    assert all(c.nullable is None for c in nodes['model.commerce.fct_orders'].columns)
    assert any(p.source=='catalog.json' for c in nodes['model.commerce.fct_orders'].columns for p in c.provenance)
    assert graph.sample and 'DuckDB' in graph.artifacts['manifest.json']['producer']


def test_unknown_metadata_and_unexecuted_tests(artifacts):
    raw=artifacts['manifest.json']['nodes']['model.commerce.fct_orders']
    raw['meta']={}
    raw['columns']={}
    graph=DbtAdapter().ingest('unknown','Unknown',artifacts['manifest.json'])
    node=next(n for n in graph.nodes if n.id==raw['unique_id'])
    assert node.grain is None and node.primary_keys is None and node.owner is None and node.columns==[]
    assert node.status=='UNKNOWN' and node.metadata['layer_classification']=='INFERENCE'
    assert all(t.status=='UNKNOWN' for t in graph.tests)


def test_compile_success_does_not_claim_build_health(artifacts):
    artifacts['run_results.json']['args']['which']='compile'
    graph=ingest(artifacts)
    assert next(n for n in graph.nodes if n.name=='int_order_items').status=='UNKNOWN'
    assert next(n for n in graph.nodes if n.name=='fct_orders').status=='FAILED'


def test_conflicts_missing_dependencies_and_unknown_status(artifacts):
    key='model.commerce.stg_orders'
    artifacts['manifest.json']['parent_map'][key]=[]
    artifacts['manifest.json']['nodes'][key]['depends_on']['nodes'].append('model.not_in_manifest')
    artifacts['catalog.json']['nodes'][key]['columns']['order_id']['type']='VARCHAR'
    artifacts['run_results.json']['metadata']['invocation_id']='different-invocation'
    artifacts['run_results.json']['results'][0]['status']='something_new'
    graph=ingest(artifacts)
    codes={i.code for i in graph.issues}
    assert {'dependency_conflict','missing_dependency','schema_conflict','invocation_mismatch','unknown_execution_status'}<=codes
    assert not any(e.from_node=='model.not_in_manifest' for e in graph.edges)


def test_freshness_failure_dominates_prior_warning(artifacts):
    key='model.commerce.fct_orders'
    artifacts['run_results.json']['results'][-1]['status']='warn'
    artifacts['sources.json']['results'].append({'unique_id':key,'status':'error','snapshotted_at':'2026-10-02T00:00:00Z'})
    assert next(n for n in ingest(artifacts).nodes if n.id==key).status=='FAILED'


@pytest.mark.parametrize('mutation',[
    lambda a:a['manifest.json'].update(nodes=[]),
    lambda a:a['manifest.json']['metadata'].update(dbt_schema_version='https://schemas.getdbt.com/dbt/manifest/v99.json'),
    lambda a:a['run_results.json'].update(results='not an array'),
    lambda a:a['run_results.json']['results'].append(a['run_results.json']['results'][0]),
])
def test_bad_artifacts_rejected_atomically(artifacts,tmp_path,mutation):
    engine=DataSystemService(MetadataStore(tmp_path/'metadata.db'))
    initial=engine.store.put(ingest(artifacts)).snapshot_id
    mutation(artifacts)
    with pytest.raises((ArtifactError,ValueError)):
        engine.import_dbt('commerce-demo','Commerce',artifacts['manifest.json'],run_results=artifacts['run_results.json'])
    assert engine.snapshot('commerce-demo').snapshot_id==initial


def test_secret_like_values_are_redacted_before_storage(artifacts):
    raw=artifacts['manifest.json']['nodes']['model.commerce.fct_orders']
    raw['raw_code']="SELECT 'sk-secretTESTVALUEabcdefgh', 'postgres://user:pass@example/db'; -- api_key=sentinelVALUE"
    raw['description']='password=sentinelVALUE'
    graph=ingest(artifacts)
    encoded=graph.model_dump_json()
    assert 'sentinelVALUE' not in encoded and 'secretTESTVALUE' not in encoded and 'user:pass' not in encoded
    assert '[REDACTED]' in encoded
