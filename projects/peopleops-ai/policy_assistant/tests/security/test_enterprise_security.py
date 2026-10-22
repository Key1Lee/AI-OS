
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from evals.evaluate_security import evaluate_security


@pytest.mark.requirement("HR-004", "HR-015")
def test_adversarial_boundaries(hr_client, enterprise_settings):
    report=evaluate_security(hr_client,enterprise_settings)
    assert report["total"] >= 18
    assert report["failed_case_ids"] == [], report


@pytest.mark.requirement("HR-004", "HR-011")
@pytest.mark.parametrize("actor,question,expected", [
    ("employee-us","What is confidential case triage?",None),
    ("sales-us","What is the remote work policy?",None),
    ("employee-uk","How do I request holiday?","HR-PTO-UK"),
    ("hr-limited","What is confidential case triage?","HR-RESTRICTED"),
    ("other-tenant","What is the parental leave policy?",None),
])
def test_access_boundaries(hr_client,actor,question,expected):
    result=hr_client.post("/ask",headers={"Authorization":"Bearer demo-"+actor},json={"question":question}).json()
    actual={c["document_id"] for c in result["citations"]}
    assert actual == ({expected} if expected else set())


@pytest.mark.requirement("HR-001", "HR-015")
def test_unauthenticated_never_reaches_sources(enterprise_settings):
    class Forbidden:
        def get_pto(self,*args):
            pytest.fail("Unauthorized record call")
    def no_retrieval(*args):
        pytest.fail("Unauthorized document access")
    with TestClient(create_app(enterprise_settings,Forbidden(),no_retrieval)) as client:
        assert client.post("/ask",json={"question":"What is my PTO balance?"}).status_code==401
        assert client.post("/ask",headers={"X-Role":"admin","X-Employee-ID":"EMP200"},json={"question":"parental leave"}).status_code==401


@pytest.mark.requirement("HR-009", "HR-015")
def test_admin_routes_errors_and_sensitive_inputs(hr_client):
    headers={"Authorization":"Bearer demo-employee-us"}
    for path in ("/health","/admin/observability","/admin/audit/missing"):
        assert hr_client.get(path).status_code==401
        assert hr_client.get(path,headers=headers).status_code==403
    assert hr_client.post("/admin/ingest",headers=headers).status_code==403
    admin={"Authorization":"Bearer demo-admin"}
    assert hr_client.get("/health",headers=admin).json()["status"]=="ok"
    assert hr_client.post("/admin/ingest",headers=admin).json()["unchanged"]==16
    assert hr_client.get("/admin/observability",headers=admin).status_code==200
    response=hr_client.post("/ask",headers=headers,json={"question":"private banking details","role":"admin"})
    assert response.status_code==422 and "private banking" not in response.text
    assert hr_client.post("/ask",headers=headers,content=b"x"*40000).status_code==413
    assert hr_client.get("/live",headers={"Host":"evil.example"}).status_code==400


@pytest.mark.requirement("HR-001", "HR-015")
def test_demo_switch_can_be_disabled(enterprise_settings):
    with TestClient(create_app(enterprise_settings.model_copy(update={"demo_mode":False}))) as client:
        assert client.get("/demo/identities").status_code==404
        assert client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"PTO balance"}).status_code==401


@pytest.mark.requirement("HR-004", "HR-006")
def test_content_not_loaded_before_acl(hr_client, monkeypatch):
    import app.rag_search as module
    original=module.suspicious_instruction
    seen=[]
    def spy(text):
        seen.append(text)
        return original(text)
    monkeypatch.setattr(module,"suspicious_instruction",spy)
    hr_client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"confidential case triage"})
    assert not any("restricted case queue" in text for text in seen)
