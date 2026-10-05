from pathlib import Path
import json
from quality_system.api import create_app
from quality_system.scenarios import ScenarioRequest, scenario_input
from quality_system.engine import validate_bundle

root = Path(__file__).resolve().parents[1]
root.joinpath("contracts").mkdir(exist_ok=True)
root.joinpath("contracts/openapi.json").write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
for corruption in [None, "duplicate", "warning", "schema"]:
    bundle = validate_bundle(scenario_input(ScenarioRequest(corruptions=[corruption] if corruption else [])))
    root.joinpath(f"contracts/{corruption or 'valid'}-example.json").write_text(bundle.model_dump_json(indent=2) + "\n")
print("Exported OpenAPI and four deterministic result/event examples.")
