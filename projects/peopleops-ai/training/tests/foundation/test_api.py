import pytest
from lab.contracts import PendingExercise
from exercises import e06_grounding


@pytest.fixture(autouse=True)
def isolate_business_exercise(monkeypatch):
    # This infrastructure test remains valid after the learner finishes E06.
    def pending(*args, **kwargs):
        raise PendingExercise("E06 test sentinel")
    monkeypatch.setattr(e06_grounding, "answer_question", pending)


def test_health_and_workbench_survive_pending_exercises(client, auth):
    assert client.get("/health").status_code == 200
    assert client.get("/lab/catalog").json()["counts"]["employees"] == 120
    response = client.post("/api/assistant", json={"text": "When is payroll paid?"}, headers=auth["employee"])
    assert response.status_code == 501
    assert response.json()["status"] == "exercise_pending"
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("path", ["/api/me", "/api/employees/EMP-001", "/api/candidates/CAN-001", "/api/jobs", "/api/requests/TKT-001"])
def test_business_routes_require_authentication(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invented", "X-Role": "hr_admin"}).status_code == 401


def test_authentication_uses_server_identity(client, auth):
    headers = dict(auth["employee"], **{"X-Role": "hr_admin"})
    assert client.get("/api/me", headers=headers).json() == {"employee_id": "EMP-001", "role": "employee"}


def test_confirmation_input_rejects_override_fields(client, auth):
    assert client.post("/api/actions/confirm", headers=auth["employee"], json={"proposal_id": "x", "confirmed": True,
            "idempotency_key": "example-key", "employee_id": "EMP-002"}).status_code == 422


def test_telemetry_does_not_store_request_text(client, auth):
    client.post("/api/assistant", headers=auth["employee"], json={"text": "private-payroll-text"})
    client.post("/lab/provider-probe")
    data = client.get("/lab/telemetry").json()
    assert data["pending_exercises"] == 1
    assert data["fake_input_words"] > 0 and data["provider_input_tokens"] == 0
    assert "private-payroll-text" not in str(data)
    assert auth["employee"]["Authorization"] not in str(data)
