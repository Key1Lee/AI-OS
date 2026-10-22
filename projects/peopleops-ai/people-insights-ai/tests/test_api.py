import csv
import io
import json

import httpx
from fastapi.testclient import TestClient

from app.data_loader import ROOT
from app.main import create_app


def test_health_frontend_and_metadata(client):
    assert client.get("/").status_code == 200
    assert "People Insights AI" in client.get("/").text
    assert client.get("/health").json()["dataset_rows"] == 1470
    assert len(client.get("/api/departments").json()["departments"]) == 3
    assert len(client.get("/api/metrics").json()["metrics"]) == 4
    assert client.get("/data/ibm_hr.csv").status_code == 404


def test_structured_report_auth_and_validation(client):
    body = {"department": "Sales", "metrics": ["job_satisfaction"]}
    assert client.post("/api/report", json=body).json()["status"] == "report"
    assert client.post("/api/report", json={**body, "role": "admin"}).status_code == 422
    assert (
        client.post("/api/report", json={**body, "department": "Marketing"}).status_code
        == 422
    )
    assert (
        client.post("/api/report", json={**body, "metrics": ["salary"]}).status_code
        == 422
    )
    client.headers["X-Demo-Key"] = "demo-sales-manager"
    assert (
        client.post(
            "/api/report", json={**body, "department": "Human Resources"}
        ).status_code
        == 403
    )
    client.headers["X-Demo-Key"] = "fake"
    assert client.post("/api/report", json=body).status_code == 401


def test_csv_principal_binding_and_unexpected_paths(client):
    result = client.post(
        "/api/report", json={"department": "Sales", "metrics": ["attrition"]}
    ).json()
    url = result["report"]["csv_url"]
    response = client.get(url)
    assert (
        response.status_code == 200
        and "attachment" in response.headers["content-disposition"]
    )
    assert len(list(csv.DictReader(io.StringIO(response.text)))) == 1
    client.headers["X-Demo-Key"] = "demo-sales-manager"
    assert client.get(url).status_code == 404


def test_data_unavailable_returns_explicit_503():
    with TestClient(create_app(data_error="IBM data unavailable")) as client:
        assert client.get("/health").status_code == 503
        assert (
            client.post(
                "/api/report",
                json={"department": "Sales", "metrics": ["attrition"]},
                headers={"X-Demo-Key": "demo-hr-manager"},
            ).status_code
            == 503
        )


def test_invalid_chat_and_no_arbitrary_url(client):
    assert (
        client.post("/api/chat", json={"session_id": "s", "message": " "}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/chat",
            json={"session_id": "s", "message": "Sales", "url": "file:///etc/passwd"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/chat/route",
            json={"session_id": "s", "message": "Sales"},
            headers={"X-Execution-Mode": "other"},
        ).status_code
        == 422
    )


def test_direct_route_uses_same_calculations(client):
    response = client.post(
        "/api/chat/route",
        json={"session_id": "direct", "message": "Sales job satisfaction"},
    ).json()
    assert response["execution_mode"] == "direct"
    assert (
        response["report"]["departments"][0]["metrics"]["job_satisfaction"]["value"]
        == 61.4
    )


def test_n8n_unavailable_is_predictable_without_automatic_replay(client, monkeypatch):
    async def fail(*args, **kwargs):
        raise httpx.ConnectError("test offline")

    monkeypatch.setattr(httpx.AsyncClient, "post", fail)
    response = client.post(
        "/api/chat/route",
        json={"session_id": "offline", "message": "Sales report"},
        headers={"X-Execution-Mode": "n8n"},
    )
    assert response.status_code == 502 and "Direct API" in response.json()["detail"]
    assert not client.app.state.sessions.items


def test_workflow_json_success_and_failure_connections():
    workflow = json.loads((ROOT / "n8n/people_insights_workflow.json").read_text())
    http_node = next(
        node for node in workflow["nodes"] if node["type"].endswith(".httpRequest")
    )
    assert http_node["parameters"]["url"].endswith("/api/chat")
    assert http_node["onError"] == "continueErrorOutput"
    assert "retryOnFail" not in http_node
    assert len(workflow["connections"][http_node["name"]]["main"]) == 2


def test_malformed_n8n_report_returns_safe_relay_error(client, monkeypatch):
    async def malformed(*args, **kwargs):
        return httpx.Response(
            200,
            json={"status": "report", "report": {"invented": 99}},
            request=httpx.Request("POST", "http://localhost/test"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", malformed)
    result = client.post(
        "/api/chat/route",
        json={"session_id": "invalid-result", "message": "Sales report"},
        headers={"X-Execution-Mode": "n8n"},
    )
    assert result.status_code == 502 and "Direct API" in result.json()["detail"]
