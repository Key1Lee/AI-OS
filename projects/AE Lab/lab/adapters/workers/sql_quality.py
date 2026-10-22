"""Quality-owned constraints, including ingress quarantine samples."""
import json
import sys
sys.dont_write_bytecode=True
from quality_system.contracts import DataContract, Dataset, ValidateRequest
from quality_system.engine import validate_bundle

if __name__=='__main__':
    p=json.load(sys.stdin)
    datasets={name:Dataset.model_validate(data) for name,data in p['datasets'].items()}
    bundles={}
    for name,contract in p['contracts'].items():
        result=validate_bundle(ValidateRequest(contract=DataContract.model_validate(contract),datasets=datasets,
            run_id=p['run_id'],executed_at=p['timestamp'])).model_dump(mode='json')
        bundles[name]=result
    print(json.dumps({'bundles':bundles,'provenance':'quality_system.engine.validate_bundle'},allow_nan=False))
