import pytest

pytestmark = pytest.mark.database


def test_own_record_is_minimal(client, auth, db_session):
    response = client.get("/api/employees/EMP-001", headers=auth["employee"])
    assert response.status_code == 200
    assert response.json()["pto_hours"] == 80
    assert "email" not in response.json() and "salary" not in response.json()


def test_other_employee_and_missing_are_indistinguishable(client, auth, db_session):
    responses = [client.get(f"/api/employees/{key}", headers=auth["employee"]) for key in ["EMP-002", "EMP-999"]]
    assert all(r.status_code == 404 for r in responses)
    assert responses[0].json() == responses[1].json()


def test_recruiter_access_and_employee_denial(client, auth, db_session):
    assert client.get("/api/candidates/CAN-001", headers=auth["recruiter"]).status_code == 200
    assert client.get("/api/candidates/CAN-001", headers=auth["employee"]).status_code == 403


def test_jobs_and_aggregate_permissions(client, auth, db_session):
    assert client.get("/api/jobs", headers=auth["employee"]).status_code == 200
    assert client.get("/api/analytics/headcount", headers=auth["analyst"]).status_code == 200
    assert client.get("/api/analytics/headcount", headers=auth["employee"]).status_code == 403
