"""Consumer translation into native arbitrary-grain quality contracts."""
import json
import sys
sys.dont_write_bytecode = True
from quality_system.contracts import DataContract, Dataset, ValidateRequest
from quality_system.engine import validate_bundle

if __name__ == "__main__":
    payload = json.load(sys.stdin)
    contract = DataContract.model_validate(payload["contract"])
    dataset = Dataset(id=contract.dataset_id, columns=contract.columns, rows=payload["rows"],
                      loaded_at=payload["timestamp"])
    bundle = validate_bundle(ValidateRequest(contract=contract,datasets={dataset.id:dataset},
        executed_at=payload["timestamp"],run_id=payload["run_id"])).model_dump(mode="json")
    print(json.dumps({"status":"PASS" if bundle["gate"]["status"]=="OPEN" and
        all(result["status"]=="PASS" for result in bundle["results"]) else "FAIL",
        "bundle":bundle,"provenance":"quality_system.engine.validate_bundle"}, allow_nan=False))
