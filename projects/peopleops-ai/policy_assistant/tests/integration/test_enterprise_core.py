import pytest


@pytest.mark.requirement("HR-002", "HR-004", "HR-014")
def test_self_pto(hr_client):
    response = hr_client.post("/ask", headers={"Authorization": "Bearer demo-employee-us"}, json={"question": "How many PTO days do I have remaining?"})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "answered"
    assert result["facts"] == {"pto_balance": "12.5", "unit": "days", "as_of_date": "2026-10-20", "source_system": "mock_workday"}
    assert hr_client.app.state.workday.transport.calls == 1


@pytest.mark.requirement("HR-003", "HR-006")
def test_policy_answer(hr_client):
    result = hr_client.post("/ask", headers={"Authorization": "Bearer demo-employee-us"}, json={"question": "What is the parental leave policy?"}).json()
    assert result["status"] == "answered", result
    assert result["citations"][0]["document_id"] == "HR-PARENTAL-US"
    assert hr_client.app.state.workday.transport.calls == 0


@pytest.mark.requirement("HR-004", "HR-015")
def test_cross_employee_denied_before_tool(hr_client):
    result = hr_client.post("/ask", headers={"Authorization": "Bearer demo-employee-us"}, json={"question": "Show me the PTO balance of EMP200."}).json()
    assert result["status"] == "denied"
    assert result["facts"] == {}
    assert hr_client.app.state.workday.transport.calls == 0
