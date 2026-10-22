"""Read-only live-stack smoke, except a benign fake provider probe."""
import httpx
from lab.config import Settings

settings = Settings()
with httpx.Client(base_url=settings.api_url, timeout=5) as client:
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"
    counts = client.get("/lab/catalog").json()["counts"]
    assert counts["employees"] == 120 and counts["jobs"] == 24 and counts["recruiting_events"] == 240
    assert client.get("/api/employees/EMP-001").status_code == 401
    identities = client.get("/lab/identities").json()
    assert len(identities) == 5
    headers = {"Authorization": "Bearer " + identities[0]["token"]}
    assert client.get("/api/me", headers=headers).json()["employee_id"] == "EMP-001"
    print("API health, seeded readiness, inventory and authentication passed")
with httpx.Client(base_url=settings.mock_url, timeout=.2) as client:
    assert len(client.get("/mock/workday").json()["items"]) == 25
    assert client.get("/mock/greenhouse?scenario=intermittent&attempt=1").status_code == 503
    assert client.get("/mock/greenhouse?scenario=intermittent&attempt=3").status_code == 200
    assert client.get("/mock/workday?scenario=schema_drift").json()["schema_version"] == 2
    try:
        client.get("/mock/workday?scenario=timeout")
    except httpx.ReadTimeout:
        print("Real socket timeout, intermittent failure, pagination and schema drift passed")
    else:
        raise AssertionError("Expected mock timeout")
print("Live-stack smoke passed")
