import json
import shutil

from fastapi.testclient import TestClient
import pytest
import yaml

from app.enterprise_data import seed_enterprise_data
from app.main import create_app
from app.mock_store import transaction
from app.models import Intent, Route

EMPLOYEE = {"Authorization":"Bearer demo-employee-us"}
ADMIN = {"Authorization":"Bearer demo-admin"}


@pytest.mark.requirement("HR-002", "HR-014")
def test_pto_comes_from_sqlite_and_unchanged_seed_preserves_edits(hr_client):
    settings = hr_client.app.state.settings
    with transaction(settings.database_path) as conn:
        row = conn.execute("SELECT record FROM mock_workday WHERE tenant='acme' AND employee_id='EMP100'").fetchone()
        record = json.loads(row[0])
        record["pto_balance"] = 10.75
        conn.execute("UPDATE mock_workday SET record=? WHERE tenant='acme' AND employee_id='EMP100'", (json.dumps(record),))
    seed_enterprise_data(settings)
    result = hr_client.post("/ask", headers=EMPLOYEE, json={"question":"What is my PTO balance?"}).json()
    assert result["facts"]["pto_balance"] == "10.75"
    source = next(s for s in result["sources"] if s["system"] == "mock_workday_database")
    assert source["returned_count"] == 1 and source["attempts"] == 1


@pytest.mark.requirement("HR-001", "HR-004", "HR-015")
def test_identity_database_revocation_prevents_source_access(hr_client):
    with transaction(hr_client.app.state.settings.database_path) as conn:
        row = conn.execute("SELECT entry FROM mock_employees WHERE employee_id='EMP100'").fetchone()
        entry = json.loads(row[0])
        entry["principal"]["active"] = False
        conn.execute("UPDATE mock_employees SET entry=? WHERE employee_id='EMP100'", (json.dumps(entry),))
    result = hr_client.post("/ask", headers=EMPLOYEE, json={"question":"What is my PTO balance?"})
    assert result.status_code == 401 and hr_client.app.state.workday.transport.calls == 0
    assert any(s["stage"]=="authentication" and s["status"]=="failed" for s in result.json()["execution_trace"])


@pytest.mark.requirement("HR-004", "HR-010", "HR-015")
def test_receipt_cannot_restore_revoked_delegation(hr_client):
    headers = {"Authorization":"Bearer demo-hr-scoped", "Idempotency-Key":"delegation-replay"}
    body = {"question":"Show me EMP110's PTO balance."}
    first = hr_client.post("/ask", headers=headers, json=body)
    assert first.json()["facts"]["pto_balance"] == "8"
    with transaction(hr_client.app.state.settings.database_path) as conn:
        row = conn.execute("SELECT entry FROM mock_employees WHERE employee_id='EMP200'").fetchone()
        entry = json.loads(row[0])
        entry["principal"]["record_scope"] = []
        conn.execute("UPDATE mock_employees SET entry=? WHERE employee_id='EMP200'", (json.dumps(entry),))
    replay = hr_client.post("/ask", headers=headers, json=body)
    assert replay.status_code == 409
    assert hr_client.post("/ask", headers={"Authorization":"Bearer demo-hr-scoped"}, json=body).json()["status"] == "denied"
    assert hr_client.app.state.workday.transport.calls == 1


@pytest.mark.requirement("HR-008", "HR-010", "HR-011")
def test_receipt_cannot_restore_removed_policy(hr_client):
    headers = {**EMPLOYEE,"Idempotency-Key":"policy-replay"}
    body = {"question":"What is our parental leave policy?"}
    assert hr_client.post("/ask", headers=headers, json=body).json()["status"] == "answered"
    with transaction(hr_client.app.state.settings.database_path) as conn:
        conn.execute("DELETE FROM inventory_membership WHERE document_id='HR-PARENTAL-US'")
    assert hr_client.post("/ask", headers=headers, json=body).status_code == 409
    assert hr_client.post("/ask", headers=EMPLOYEE, json=body).json()["status"] == "abstained"


@pytest.mark.requirement("HR-003", "HR-005", "HR-009")
@pytest.mark.parametrize("question,expected", [("What is my PTO balance?","answered"),("What is our parental leave policy?","answered"),("Show me EMP200's PTO balance.","denied")])
def test_inspectors_describe_real_authorized_work(hr_client, question, expected):
    result = hr_client.post("/ask", headers=EMPLOYEE, json={"question":question}).json()
    assert result["status"] == expected and result["duration_ms"] > 0
    stages = {s["stage"]:s for s in result["execution_trace"]}
    assert stages["authentication"]["status"] == "passed"
    assert all(s["duration_ms"] >= 0 for s in stages.values())
    assert result["applied_rules"] and all(r["source"].startswith("config/") for r in result["applied_rules"])
    diagnostics = json.dumps({key:result[key] for key in ("execution_trace","sources","applied_rules")})
    assert "EMP100" not in diagnostics and "EMP200" not in diagnostics and "demo-employee-us" not in diagnostics
    if expected == "denied":
        assert stages["retrieval"]["status"] == "skipped" and stages["authorization"]["status"] == "denied"
        assert result["sources"][1]["access"] == "blocked" and result["sources"][1]["attempts"] == 0
        assert result["facts"] == {} and result["citations"] == []


@pytest.mark.requirement("HR-007", "HR-010", "HR-011")
@pytest.mark.parametrize("scenario,status,attempts", [("normal","answered",1),("unavailable","unavailable",3),("timeout","unavailable",3),("rate_limited","unavailable",3),("intermittent","answered",3),("missing","abstained",1),("stale","abstained",1),("malformed","unavailable",1),("wrong_owner","unavailable",1)])
def test_request_scoped_failures_are_real_and_isolated(hr_client, scenario, status, attempts):
    body = {"question":"What is my PTO balance?","scenario":scenario}
    response = hr_client.post("/lab/ask", headers=EMPLOYEE, json=body)
    assert response.status_code == 200
    result = response.json()
    source = next(s for s in result["sources"] if s["system"]=="mock_workday_database")
    assert result["status"] == status and source["attempts"] == attempts
    if status != "answered":
        assert result["facts"] == {} and result["failure_code"] and result["handled_safely"]
        assert any(s["status"]=="failed" for s in result["execution_trace"])
        assert "deterministic_response" not in result["trace"]
    # A failure injection must not mutate the shared client or stored record.
    normal = hr_client.post("/ask", headers=EMPLOYEE, json={"question":"What is my PTO balance?"}).json()
    assert normal["facts"]["pto_balance"] == "12.5"
    assert hr_client.app.state.workday.transport.calls == 1


@pytest.mark.requirement("HR-004", "HR-007", "HR-015")
def test_failure_simulation_cannot_bypass_authorization(hr_client):
    result = hr_client.post("/lab/ask", headers=EMPLOYEE, json={"question":"Show me EMP200's PTO balance.","scenario":"normal"}).json()
    assert result["status"] == "denied" and result["sources"][1]["attempts"] == 0
    assert result["facts"] == {}
    invalid = hr_client.post("/lab/ask", headers=EMPLOYEE, json={"question":"PTO balance","scenario":"normal","role":"hr_admin"})
    assert invalid.status_code == 422


@pytest.mark.requirement("HR-004", "HR-014", "HR-015")
def test_optional_router_cannot_grant_record_access(enterprise_settings):
    class Router:
        def route(self, question):
            return Route(intent=Intent.PTO_BALANCE, target_employee="EMP200", rule_id="RT-PTO")
    with TestClient(create_app(enterprise_settings, router=Router())) as client:
        result = client.post("/ask", headers=EMPLOYEE, json={"question":"What is my PTO balance?"})
        assert result.json()["status"] == "denied" and client.app.state.workday.transport.calls == 0


@pytest.mark.requirement("HR-007", "HR-011")
def test_business_freshness_configuration_is_enforced(enterprise_settings, tmp_path):
    directory = tmp_path/"rules"
    shutil.copytree(enterprise_settings.rules_root, directory)
    path = directory/"business_rules.yaml"
    config = yaml.safe_load(path.read_text())
    config["max_record_age_days"] = 0
    path.write_text(yaml.safe_dump(config))
    settings = enterprise_settings.model_copy(update={"rules_root":directory})
    with TestClient(create_app(settings)) as client:
        with transaction(settings.database_path) as conn:
            row = json.loads(conn.execute("SELECT record FROM mock_workday WHERE employee_id='EMP100'").fetchone()[0])
            row["as_of_date"] = "2026-10-19"
            conn.execute("UPDATE mock_workday SET record=? WHERE employee_id='EMP100'", (json.dumps(row),))
        result = client.post("/ask", headers=EMPLOYEE, json={"question":"What is my PTO balance?"}).json()
        assert result["status"] == "abstained" and result["failure_code"] == "stale"


@pytest.mark.requirement("HR-002", "HR-007", "HR-015")
@pytest.mark.parametrize("stored", ["not JSON", "[]", "null", '{"pto_balance":"private invalid source"}'])
def test_malformed_database_record_is_not_exposed(hr_client, stored):
    with transaction(hr_client.app.state.settings.database_path) as conn:
        conn.execute("UPDATE mock_workday SET record=? WHERE employee_id='EMP100'", (stored,))
    result = hr_client.post("/ask", headers=EMPLOYEE, json={"question":"What is my PTO balance?"}).json()
    assert result["status"] == "unavailable" and result["failure_code"] == "malformed"
    assert result["facts"] == {} and "private invalid source" not in json.dumps(result)


class JobSpy:
    def __init__(self):
        self.calls = []
    def start(self, suite, tenant):
        self.calls.append((suite,tenant))
        return {"job_id":"0"*36,"status":"queued","tests":None}
    def recent(self, tenant):
        return []
    def get(self, job_id, tenant):
        return {"job_id":job_id,"status":"running","tests":None}
    def close(self):
        pass


@pytest.mark.requirement("HR-012", "HR-015")
def test_test_runner_requires_explicit_permission_and_fixed_inputs(enterprise_settings):
    spy = JobSpy()
    with TestClient(create_app(enterprise_settings, test_runner=spy)) as client:
        assert not client.get("/lab/info",headers=EMPLOYEE).json()["can_run_tests"]
        assert client.get("/lab/info",headers=ADMIN).json()["can_run_tests"]
        for headers in ({},EMPLOYEE,{"Authorization":"Bearer demo-hr-scoped"}):
            assert client.post("/admin/test-runs",headers=headers,json={"suite":"unit"}).status_code in (401,403)
        for body in ({"suite":"unit; echo secret"},{"suite":"unit","command":"private"},{"suite":"unit","output":"/tmp/private"}):
            assert client.post("/admin/test-runs",headers=ADMIN,json=body).status_code == 422
        assert spy.calls == []
        assert client.post("/admin/test-runs",headers=ADMIN,json={"suite":"unit"}).status_code == 202
        assert spy.calls == [("unit","acme")]
        assert client.get("/admin/test-runs",headers=ADMIN).json() == {"jobs":[]}
        assert client.get("/admin/test-runs/"+"0"*36,headers=ADMIN).json()["status"] == "running"


@pytest.mark.requirement("HR-001", "HR-015")
def test_testing_layer_can_be_disabled(enterprise_settings):
    with TestClient(create_app(enterprise_settings.model_copy(update={"lab_enabled":False}))) as client:
        assert client.get("/lab/info",headers=ADMIN).status_code == 404
        assert client.post("/lab/ask",headers=EMPLOYEE,json={"question":"PTO balance"}).status_code == 404
        assert client.post("/admin/test-runs",headers=ADMIN,json={"suite":"unit"}).status_code == 404
        assert client.post("/ask",headers=EMPLOYEE,json={"question":"PTO balance"}).json()["status"] == "answered"
