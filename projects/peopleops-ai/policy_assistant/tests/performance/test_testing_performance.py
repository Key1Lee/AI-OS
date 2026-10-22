from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.mark.requirement("HR-009", "HR-010")
def test_slow_source_has_measured_stage_time(hr_client):
    result = hr_client.post("/lab/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"What is my PTO balance?","scenario":"slow"}).json()
    retrieval = next(s for s in result["execution_trace"] if s["stage"]=="retrieval")
    assert result["status"] == "answered" and result["facts"]["pto_balance"] == "12.5"
    assert retrieval["duration_ms"] >= 20
    assert result["duration_ms"] >= retrieval["duration_ms"]


@pytest.mark.requirement("HR-007", "HR-010")
def test_concurrent_fault_profiles_do_not_cross_requests(hr_client):
    cases = [("normal","answered",1),("unavailable","unavailable",3),("missing","abstained",1),("intermittent","answered",3)]
    def request(case):
        scenario, status, attempts = case
        result = hr_client.post("/lab/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"What is my PTO balance?","scenario":scenario}).json()
        source = next(s for s in result["sources"] if s["system"]=="mock_workday_database")
        return result["status"]==status and source["attempts"]==attempts
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(request,cases))
