import pytest
from exercises.e07_authorization import authorize
from lab.contracts import Principal


@pytest.mark.parametrize("role,actor,action,resource,allowed", [
    ("employee", "EMP-001", "employee_read", {"employee_id": "EMP-001"}, True),
    ("employee", "EMP-001", "employee_read", {"employee_id": "EMP-002"}, False),
    ("manager", "EMP-002", "employee_read", {"employee_id": "EMP-006", "manager_id": "EMP-002"}, False),
    ("manager", "EMP-002", "manager_summary", {"employee_id": "EMP-006", "manager_id": "EMP-002"}, True),
    ("hr_admin", "EMP-004", "employee_read", {"employee_id": "EMP-001"}, True),
    ("recruiter", "EMP-003", "candidate_read", {"candidate_id": "CAN-001"}, True),
    ("employee", "EMP-001", "candidate_read", {"candidate_id": "CAN-001"}, False),
    ("analyst", "EMP-005", "analytics_read", {}, True),
    ("employee", "EMP-001", "analytics_read", {}, False),
    ("employee", "EMP-001", "policy_read", {"audience": "all"}, True),
    ("employee", "EMP-001", "policy_read", {"audience": "hr_admin"}, False),
    ("hr_admin", "EMP-004", "unknown_operation", {}, False),
    ("employee", "EMP-001", "pto_create", {"employee_id": "EMP-002"}, False),
    ("employee", "EMP-001", "ticket_create", {"employee_id": "EMP-001"}, True),
])
def test_permission_matrix(role, actor, action, resource, allowed):
    assert authorize(Principal(employee_id=actor, role=role), action, resource) is allowed
