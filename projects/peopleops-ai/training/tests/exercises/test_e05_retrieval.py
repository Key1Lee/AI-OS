import pytest
from exercises.e05_retrieval import retrieve
from lab.contracts import Principal

pytestmark = pytest.mark.database
EMPLOYEE = Principal(employee_id="EMP-001", role="employee")


def test_retrieves_current_exact_policy(db_session):
    hits = retrieve("Full-time employees receive hours of PTO per calendar year", EMPLOYEE, db_session)
    assert hits and hits[0]["policy_id"] == "PTO" and hits[0]["version"] == 2
    assert not any(h["version"] == 1 for h in hits)


def test_filters_restricted_before_top_k(db_session):
    hits = retrieve("Compensation planning worksheets", EMPLOYEE, db_session, k=1)
    assert all(h["policy_id"] != "COMP" for h in hits)


def test_hr_can_retrieve_restricted_policy(db_session):
    hits = retrieve("Compensation planning worksheets", Principal(employee_id="EMP-004", role="hr_admin"), db_session)
    assert any(h["policy_id"] == "COMP" for h in hits)
