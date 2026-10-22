import json
import pytest
from fastapi.testclient import TestClient
from peopleops.app import create_app
from peopleops.config import Settings
from peopleops.db import connect


def test_health_and_ready(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").status_code == 200


def test_authentication_cannot_be_forged(client,auth):
    assert client.get("/api/metrics").status_code == 401
    assert client.get("/api/metrics",headers={"Authorization":"Bearer forged","X-Role":"hr"}).status_code == 401
    assert client.get("/api/metrics",headers={**auth["maya"],"X-Role":"hr"}).status_code == 403
    assert client.get("/health",headers={"Host":"malicious.example"}).status_code == 400


def test_demo_switch_can_be_disabled(settings):
    with TestClient(create_app(Settings(data_dir=settings.data_dir,demo_mode=False))) as c:
        assert c.get("/api/demo/identities").status_code == 404


def test_employee_ownership(client,auth):
    assert client.get("/api/employees/EMP-001",headers=auth["maya"]).json()["full_name"] == "Maya Chen"
    assert client.get("/api/employees/EMP-002",headers=auth["maya"]).status_code == 403
    tickets = client.get("/api/requests",headers=auth["maya"]).json()
    assert len(tickets) == 1
    assert all(r["employee_id"] == "EMP-001" for r in tickets)
    assert client.get("/api/employees",headers=auth["maya"]).status_code == 403


@pytest.mark.parametrize("path",["/api/employees","/api/employees/EMP-001","/api/requests","/api/onboarding","/api/ops","/api/audit","/api/notifications"])
def test_analyst_has_aggregate_access_only(client,auth,path):
    assert client.get(path,headers=auth["analyst"]).status_code == 403
    result = client.get("/api/metrics",headers=auth["analyst"])
    assert result.status_code == 200
    assert "salary" not in result.text and "@fictional" not in result.text


def test_hr_directory_pagination_omits_salary(client,auth):
    result = client.get("/api/employees?limit=5&offset=5",headers=auth["hr"])
    assert result.status_code == 200
    assert len(result.json()["items"]) == 5
    assert result.json()["total"] == 16
    assert "salary" not in result.text
    assert client.get("/api/employees?limit=999",headers=auth["hr"]).status_code == 422


def test_ticket_idempotency_and_conflict(client,auth):
    headers = {**auth["maya"],"Idempotency-Key":"test-payroll-001"}
    payload = {"subject":"Payroll help","description":"My payslip is missing."}
    first = client.post("/api/requests",headers=headers,json=payload)
    second = client.post("/api/requests",headers=headers,json=payload)
    assert (first.status_code,second.status_code) == (201,200)
    assert first.json()["request"]["request_id"] == second.json()["request"]["request_id"]
    assert first.json()["request"]["team"] == "Payroll"
    assert second.json()["replayed"] is True
    assert client.post("/api/requests",headers=headers,json={**payload,"subject":"Different content"}).status_code == 409
    assert len(client.get("/api/requests",headers=auth["maya"]).json()) == 2


def test_ticket_validation_and_impersonation(client,auth):
    headers = {**auth["maya"],"Idempotency-Key":"test-owner-001"}
    assert client.post("/api/requests",headers=headers,json={"subject":"","description":"x"}).status_code == 422
    assert client.post("/api/requests",headers=headers,json={"subject":"Payroll help","description":"Need payroll assistance.","employee_id":"EMP-002"}).status_code == 403
    assert client.post("/api/requests",headers=auth["maya"],json={"subject":"Payroll help","description":"Need payroll assistance."}).status_code == 422


def test_resolving_tickets_is_hr_only(client,auth,settings):
    assert client.patch("/api/requests/HR-001",headers=auth["maya"],json={"status":"resolved"}).status_code == 403
    assert client.patch("/api/requests/HR-001",headers=auth["hr"],json={"status":"resolved"}).status_code == 200
    with connect(settings) as conn:
        assert conn.execute("SELECT resolved_at FROM hr_requests WHERE request_id='HR-001'").fetchone()[0]


def test_onboarding_cannot_be_changed_by_other_employees(client,auth):
    tasks = client.get("/api/onboarding",headers=auth["hr"]).json()
    task = tasks[0]
    assert client.patch(f"/api/onboarding/{task['task_id']}",headers=auth["maya"],json={"status":"completed"}).status_code == 403
    assert client.patch(f"/api/onboarding/{task['task_id']}",headers=auth["hr"],json={"status":"completed"}).status_code == 200


def test_audit_and_telemetry_do_not_store_request_bodies_or_tokens(client,auth,settings):
    marker = "CONFIDENTIAL-SYNTHETIC-MARKER"
    client.post("/api/requests",headers={**auth["maya"],"Idempotency-Key":"private-marker-001"},json={"subject":"Payroll question","description":marker})
    client.get("/api/employees/EMP-002",headers=auth["maya"])
    with connect(settings) as conn:
        audit_text = json.dumps([dict(r) for r in conn.execute("SELECT * FROM audit_logs")])
        telemetry_text = json.dumps([dict(r) for r in conn.execute("SELECT * FROM http_observations")])
        assert marker not in audit_text + telemetry_text
        assert auth["maya"]["Authorization"] not in audit_text + telemetry_text
        assert conn.execute("SELECT 1 FROM audit_logs WHERE action='employee.read' AND outcome='denied'").fetchone()
        assert conn.execute("SELECT 1 FROM http_observations WHERE route='/api/employees/{employee_id}'").fetchone()


def test_sql_injection_is_stored_as_text(client,auth):
    result=client.post("/api/requests",headers={**auth["maya"],"Idempotency-Key":"injection-test-001"},json={"subject":"Payroll question","description":"'); DROP TABLE employees; --"})
    assert result.status_code == 201
    assert client.get("/api/metrics",headers=auth["hr"]).json()["headcount"] == 14


def test_failure_and_recovery_surface_readiness(client,auth):
    assert client.post("/api/ops/pipeline",headers=auth["hr"],json={"scenario":"unavailable"}).status_code == 503
    assert client.get("/ready").status_code == 503
    assert client.post("/api/ops/pipeline",headers=auth["hr"],json={"scenario":"normal"}).status_code == 200
    assert client.get("/ready").status_code == 200


def test_headers_and_openapi_contract(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Frame-Options"] == "DENY"
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/api/requests"]["post"]["security"] == [{"HTTPBearer":[]}]
