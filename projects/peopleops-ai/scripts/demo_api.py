"""Safe local API demo; no tokens or confidential descriptions are printed."""
from uuid import uuid4
import httpx

with httpx.Client(base_url="http://127.0.0.1:8765", timeout=10) as client:
    response = client.get("/api/demo/identities")
    response.raise_for_status()
    maya = next(item for item in response.json() if item["principal_id"] == "maya")
    headers = {"Authorization": f"Bearer {maya['token']}", "Idempotency-Key": str(uuid4())}
    body = {"subject": "Payroll help", "description": "My fictional payslip is missing."}
    first = client.post("/api/requests", headers=headers, json=body)
    first.raise_for_status()
    second = client.post("/api/requests", headers=headers, json=body)
    second.raise_for_status()
    assert first.json()["request"]["request_id"] == second.json()["request"]["request_id"]
    print(f"Created: HTTP {first.status_code}, routed to {first.json()['request']['team']}")
    print(f"Replay: HTTP {second.status_code}, same request ID")
    denied = client.get("/api/employees/EMP-002", headers=headers)
    assert denied.status_code == 403
    print("Privacy: another employee's record returns HTTP 403")
