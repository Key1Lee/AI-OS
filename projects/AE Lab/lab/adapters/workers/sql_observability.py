"""Native snapshot/lineage/incident evidence; declared dbt-shaped adapter artifacts."""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
from data_system_map import create_service

if __name__=='__main__':
    p=json.load(sys.stdin);service=create_service(Path(p['database']),seed_demo=False)
    snap=service.import_dbt(p['system_id'],'AE SQL learning evidence',p['manifest'],run_results=p['run_results'])
    print(json.dumps({'snapshot_id':snap.snapshot_id,'nodes':[n.model_dump(mode='json') for n in snap.nodes],
        'edges':[e.model_dump(mode='json') for e in snap.edges],
        'incidents':service.incidents(p['system_id'],snapshot_id=snap.snapshot_id),
        'provenance':'data_system_map.create_service / import_dbt; AE-produced metadata, no dbt execution'},allow_nan=False))
