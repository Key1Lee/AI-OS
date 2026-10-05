"""Export the API's provider-neutral definitions and schemas without a running server."""

import json
from pathlib import Path

from data_modeling_lab.api import create_app
from fastapi.testclient import TestClient

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "docs" / "contracts.json"
    with TestClient(create_app()) as client:
        response = client.get("/api/contracts")
        response.raise_for_status()
        target.write_text(json.dumps(response.json(), indent=2) + "\n")
    print(target)
