from fastapi.testclient import TestClient
import pytest


def plain_client(client):
    return TestClient(client.app, base_url="http://127.0.0.1")


@pytest.mark.parametrize("path", ["/", "/api/health", "/api/config", "/api/sessions", "/api/dashboard"])
def test_hostile_host_cannot_read_original_app(app_factory, path):
    client, provider, database, _ = app_factory()
    response = plain_client(client).get(path, headers={"Host": "attacker.example"})
    assert response.status_code == 400
    assert database.list_sessions() == [] and provider.calls == []


@pytest.mark.parametrize("origin", [
    "https://attacker.example", "http://localhost", "http://127.0.0.1:9000",
    "https://127.0.0.1", "null", "", "http://[", "http://127.0.0.1/path",
    "http://user@127.0.0.1", "http://127.0.0.1?query=x",
    "http://127.0.0.1?", "http://127.0.0.1#",
])
def test_invalid_origin_rejects_even_with_token(app_factory, start_session, origin):
    client, provider, database, _ = app_factory()
    session = start_session(client)
    response = client.post(f"/api/sessions/{session['id']}/pause", headers={"Origin": origin})
    assert response.status_code == 403 and response.json()["code"] == "local_origin"
    assert database.get_session(session["id"])["status"] == "ACTIVE"
    assert provider.calls == []


@pytest.mark.parametrize("suffix", ["", "/submit", "/pause", "/resume", "/continue", "/sync"])
@pytest.mark.parametrize("token", [None, "incorrect", b"\xe9"])
def test_every_mutation_requires_token_before_route_work(app_factory, start_session, suffix, token):
    client, provider, database, _ = app_factory()
    session = start_session(client)
    path = "/api/sessions" if suffix == "" else f"/api/sessions/{session['id']}{suffix}"
    response = plain_client(client).post(path, json={}, headers={} if token is None else {"X-Interview-Token": token})
    assert response.status_code == 403 and response.json()["code"] == "local_token"
    assert len(database.list_sessions()) == 1
    assert database.get_session(session["id"])["status"] == "ACTIVE"
    assert provider.calls == []


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_boundary_covers_all_unsafe_methods(app_factory, method):
    client, provider, database, _ = app_factory()
    response = getattr(plain_client(client), method)("/api/sessions")
    assert response.status_code == 403
    assert database.list_sessions() == [] and provider.calls == []


def test_form_pause_rejected_and_valid_local_client_allowed(app_factory, start_session):
    client, provider, database, _ = app_factory()
    session = start_session(client)
    pause = f"/api/sessions/{session['id']}/pause"
    rejected = plain_client(client).post(pause, data={"unused": "1"}, headers={"Origin": "https://attacker.example"})
    assert rejected.status_code == 403
    assert database.get_session(session["id"])["status"] == "ACTIVE"
    assert client.post(pause, headers={"Origin": "http://127.0.0.1"}).status_code == 200
    assert client.post(f"/api/sessions/{session['id']}/resume").status_code == 200
    assert provider.calls == []
    assert "unsafe-inline" not in rejected.headers["Content-Security-Policy"]


def test_token_rotates_between_process_instances(app_factory):
    first, _, _, _ = app_factory()
    second, provider, database, _ = app_factory()
    old_token = first.get("/api/config").json()["request_token"]
    assert old_token != second.get("/api/config").json()["request_token"]
    rejected = second.post("/api/sessions", json={"target_role": "Senior FDE"}, headers={"X-Interview-Token": old_token})
    assert rejected.status_code == 403
    assert database.list_sessions() == [] and provider.calls == []
