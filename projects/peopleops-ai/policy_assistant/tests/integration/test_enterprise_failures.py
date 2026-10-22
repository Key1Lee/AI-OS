from datetime import date
from decimal import Decimal
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import PTORecord
from app.mock_store import transaction
from app.workday_client import MockWorkdayClient, MockWorkdayTransport, RecordError
from app.audit import metrics, percentile, write_audit
from tests.unit.test_enterprise_units import principal


@pytest.mark.requirement("HR-007", "HR-010", "HR-011")
@pytest.mark.parametrize("scenario,status,calls", [("unavailable","upstream_503",3),("timeout","timeout",3),("rate_limited","rate_limited",3),("missing","missing",1),("malformed","malformed",1),("stale","stale",1),("wrong_owner","invalid_scope",1)])
def test_retry_bounds(enterprise_settings, scenario,status,calls):
    transport=MockWorkdayTransport(enterprise_settings.fixture_root/"workday_pto.json",scenario)
    sleeps=[]
    client=MockWorkdayClient(enterprise_settings,transport,sleep=sleeps.append)
    with pytest.raises(RecordError) as error:
        client.get_pto(principal(),"EMP100")
    assert error.value.status == status
    assert error.value.attempts == calls and transport.calls == calls
    assert len(sleeps) == max(0,calls-1) and all(delay <= .2 for delay in sleeps)


@pytest.mark.requirement("HR-010", "HR-014")
def test_injected_adapters(enterprise_settings):
    class Source:
        calls=0
        def get_pto(self,actor,target):
            self.calls+=1
            return PTORecord(employee_id=target,tenant=actor.tenant,pto_balance=Decimal("3.25"),unit="hours",as_of_date=date(2026,10,20)),1
    def forbidden_retriever(*args):
        pytest.fail("Record workflow must not call policy retrieval")
    source=Source()
    with TestClient(create_app(enterprise_settings,source,forbidden_retriever)) as client:
        response=client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"What is my PTO balance?"})
        assert response.json()["facts"]["pto_balance"] == "3.25"
        client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"PTO for EMP200"})
        assert source.calls == 1


@pytest.mark.requirement("HR-007", "HR-011")
@pytest.mark.parametrize("question,status", [("What is the sabbatical policy?","abstained"),("What is the travel meal daily limit?","abstained"),("I need help","clarify"),("Does insurance cover surgery?","escalated")])
def test_safe_failures(hr_client,question,status):
    result=hr_client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":question}).json()
    assert result["status"] == status
    assert result["facts"] == {} and result["citations"] == []


@pytest.mark.requirement("HR-006")
def test_exact_citations(hr_client):
    result=hr_client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"How do I request PTO?"}).json()
    citation=result["citations"][0]
    assert citation["version"]=="2.1"
    assert "five business days" in citation["quote"] and result["answer"].endswith(citation["quote"])
    with transaction(hr_client.app.state.settings.database_path) as conn:
        source=conn.execute("SELECT full_text FROM indexed_documents WHERE document_id=? AND version=?",(citation["document_id"],citation["version"])).fetchone()[0]
        assert citation["quote"] in source


@pytest.mark.requirement("HR-009")
def test_redacted_audit(hr_client,caplog):
    with caplog.at_level("INFO",logger="peopleops.enterprise.audit"):
        result=hr_client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"What is my PTO balance?"}).json()
    with transaction(hr_client.app.state.settings.database_path) as conn:
        events=[json.loads(row[0]) for row in conn.execute("SELECT event FROM audits")]
        assert events[-1]["attempts"]==1 and events[-1]["source_status"]=="fresh"
        assert metrics(conn)["requests"]==1
        with pytest.raises(ValueError,match="allowlisted"):
            write_audit(conn,{"request_id":"test","question":"private"})
    serialized=json.dumps(events)+caplog.text
    for forbidden in ["EMP100","EMP200","demo-employee-us","What is my PTO balance?","pto_balance"]:
        assert forbidden not in serialized
    response=hr_client.get("/admin/audit/"+result["request_id"],headers={"Authorization":"Bearer demo-admin"})
    assert response.json()["events"][0]["request_id"]==result["request_id"]
    assert percentile([], .95)==0


@pytest.mark.requirement("HR-007", "HR-009", "HR-010")
def test_storage_error_is_sanitized(hr_client,monkeypatch):
    from contextlib import contextmanager
    import sqlite3
    import app.main as module
    @contextmanager
    def unavailable(*args,**kwargs):
        raise sqlite3.OperationalError("private database path and EMP100")
        yield
    monkeypatch.setattr(module,"transaction",unavailable)
    response=hr_client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"PTO balance"})
    assert response.status_code==503
    assert "EMP100" not in response.text and "private database" not in response.text
