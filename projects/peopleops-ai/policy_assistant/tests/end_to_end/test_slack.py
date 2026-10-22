from concurrent.futures import ThreadPoolExecutor
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.auth import slack_signature
from app.main import create_app


def delivery(client, question, event_id="EV_TEST", actor="employee-us", user="U100", team="T_DEMO", timestamp=None, signature=None, raw=None):
    envelope={"type":"event_callback","team_id":team,"event_id":event_id,"event":{"type":"app_mention","user":user,"text":question}}
    body=json.dumps(envelope,separators=(",",":")).encode() if raw is None else raw
    stamp=str(int(time.time()) if timestamp is None else timestamp)
    secret=client.app.state.settings.slack_signing_secret.get_secret_value()
    headers={"Content-Type":"application/json","Authorization":"Bearer demo-"+actor,
             "X-Slack-Request-Timestamp":stamp,"X-Slack-Signature":signature or slack_signature(body,stamp,secret)}
    return client.post("/slack/events",content=body,headers=headers)


@pytest.mark.requirement("HR-001", "HR-002", "HR-003", "HR-004", "HR-005", "HR-006")
@pytest.mark.parametrize("question,status,document", [
    ("How many PTO days do I have remaining?","answered",None),
    ("What is the parental leave policy?","answered","HR-PARENTAL-US"),
    ("Show me the PTO balance of EMP200.","denied",None),
])
def test_signed_slack_core_workflows(hr_client,question,status,document):
    response=delivery(hr_client,question)
    assert response.status_code==200
    data=response.json()
    assert data["status"]==status
    assert data["request_id"]==response.headers["x-request-id"]
    assert "enterprise_identity" in data["trace"] and "redacted_audit" in data["trace"]
    if document:
        assert data["citations"][0]["document_id"]==document
    if "remaining" in question:
        assert data["facts"]["pto_balance"]=="12.5"


@pytest.mark.requirement("HR-001", "HR-007", "HR-015")
@pytest.mark.parametrize("options,http_status", [
    ({"signature":"v0=bad"},401), ({"timestamp":0},401), ({"actor":"invalid"},401),
    ({"user":"U200"},403), ({"team":"T_OTHER"},403), ({"raw":b'{"secret":"private input"'},422),
])
def test_signed_slack_rejections(hr_client,options,http_status):
    response=delivery(hr_client,"PTO balance",**options)
    assert response.status_code==http_status
    assert hr_client.app.state.workday.transport.calls==0
    assert "private input" not in response.text


@pytest.mark.requirement("HR-010", "HR-014")
def test_duplicate_events_and_conflicts(hr_client):
    first=delivery(hr_client,"What is my PTO balance?")
    second=delivery(hr_client,"What is my PTO balance?")
    for field in ("status", "answer", "intent", "facts", "citations", "request_id", "requirement_ids", "escalation"):
        assert first.json()[field] == second.json()[field]
    assert not first.json()["replayed"] and second.json()["replayed"]
    assert "mock_workday" not in second.json()["trace"]
    stages = {s["stage"]:s for s in second.json()["execution_trace"]}
    assert stages["retrieval"]["status"] == "skipped" and stages["response"]["status"] == "passed"
    assert sum(s["duration_ms"] for s in stages.values()) <= second.json()["duration_ms"]+1
    assert hr_client.app.state.workday.transport.calls==1
    conflict=delivery(hr_client,"How do I request PTO?")
    assert conflict.status_code==409
    assert hr_client.app.state.workday.transport.calls==1


@pytest.mark.requirement("HR-010", "HR-015")
def test_concurrent_duplicate_event(hr_client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:delivery(hr_client,"What is my PTO balance?"),range(8)))
    assert {r.status_code for r in responses}=={200}
    assert len({r.json()["request_id"] for r in responses})==1
    assert hr_client.app.state.workday.transport.calls==1


@pytest.mark.requirement("HR-004", "HR-010")
def test_receipts_are_bound_to_principal(hr_client):
    us=delivery(hr_client,"What is my PTO balance?")
    sales=delivery(hr_client,"What is my PTO balance?",actor="sales-us",user="U110")
    assert us.json()["facts"]["pto_balance"]=="12.5"
    assert sales.json()["facts"]["pto_balance"]=="8"
    assert hr_client.app.state.workday.transport.calls==2


@pytest.mark.requirement("HR-010")
def test_portal_idempotency_and_rate_limit(enterprise_settings):
    settings=enterprise_settings.model_copy(update={"max_requests_per_minute":3})
    with TestClient(create_app(settings)) as client:
        headers={"Authorization":"Bearer demo-employee-us","Idempotency-Key":"key-one"}
        body={"question":"What is my PTO balance?"}
        first=client.post("/ask",headers=headers,json=body)
        repeated=client.post("/ask",headers=headers,json=body)
        assert repeated.json()["facts"]==first.json()["facts"] and repeated.json()["request_id"]==first.json()["request_id"]
        assert repeated.json()["replayed"] and "mock_workday" not in repeated.json()["trace"]
        bad=client.post("/ask",headers={**headers,"Idempotency-Key":"invalid key"},json=body)
        assert bad.status_code==422
        assert client.post("/ask",headers=headers,json=body).status_code==429
        assert client.app.state.workday.transport.calls==1
