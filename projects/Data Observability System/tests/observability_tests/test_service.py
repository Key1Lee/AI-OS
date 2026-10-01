from data_system_map.repository import MetadataStore
from data_system_map.service import DataSystemService
from observability_tests.test_adapter import ingest


def test_snapshot_reopen_and_evidence_supported_incident(artifacts,tmp_path):
    path=tmp_path/'metadata.db'
    engine=DataSystemService(MetadataStore(path))
    frozen=engine.store.put(ingest(artifacts))
    reopened=DataSystemService(MetadataStore(path))
    assert reopened.snapshot('commerce-demo').model_dump()==frozen.model_dump()
    evidence=reopened.investigate('commerce-demo','model.commerce.fct_orders',reveal_diagnostics=True)
    assert evidence['first_suspicious_node']=='model.commerce.int_order_items'
    assert evidence['last_known_good']==['model.commerce.stg_orders']
    assert evidence['first_bad_node'] is None
    assert evidence['inference']['classification']=='INFERENCE'
    assert {n['name'] for n in evidence['impact']['affected_outputs']}=={'Daily Revenue','Executive Dashboard'}
    assert evidence['uncertainty']


def test_insufficient_comparable_evidence_keeps_origin_unknown(artifacts,tmp_path):
    snapshot=ingest(artifacts)
    snapshot.observations=[o for o in snapshot.observations if o.node_id!='model.commerce.stg_orders']
    engine=DataSystemService(MetadataStore(tmp_path/'metadata.db'));engine.store.put(snapshot)
    evidence=engine.investigate('commerce-demo','model.commerce.fct_orders',reveal_diagnostics=True)
    assert evidence['first_suspicious_node'] is None
    assert evidence['first_bad_node'] is None


def test_overview_is_progressive_and_column_lineage_is_honest(artifacts,tmp_path):
    engine=DataSystemService(MetadataStore(tmp_path/'metadata.db'));engine.store.put(ingest(artifacts))
    overview=engine.graph('commerce-demo')
    assert len(overview['stages'])==5 and overview['nodes']==[]
    models=engine.graph('commerce-demo',level='models',focus='model.commerce.fct_orders')
    assert {n['name'] for n in models['nodes']}=={'int_order_items','fct_orders','mart_revenue'}
    from data_system_map.graph import Graph
    assert Graph(engine.snapshot('commerce-demo')).column_lineage('model.commerce.fct_orders','order_id')['status']=='unavailable'


def test_new_metadata_snapshot_does_not_rewrite_old(artifacts,tmp_path):
    engine=DataSystemService(MetadataStore(tmp_path/'metadata.db'))
    initial=engine.store.put(ingest(artifacts))
    artifacts['manifest.json']['nodes']['model.commerce.fct_orders']['description']='A revised declared description.'
    latest=engine.store.put(ingest(artifacts))
    assert initial.snapshot_id!=latest.snapshot_id
    assert engine.snapshot('commerce-demo',initial.snapshot_id).model_dump()==initial.model_dump()
    assert engine.changed_nodes('commerce-demo')['nodes']==['model.commerce.fct_orders']
