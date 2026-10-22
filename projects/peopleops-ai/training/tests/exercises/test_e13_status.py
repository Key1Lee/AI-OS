import pytest
from fastapi import HTTPException
from lab.contracts import Principal
from exercises.e13_status import request_status

pytestmark = pytest.mark.database


def test_owned_status(db_session):
    assert request_status("TKT-001", Principal(employee_id="EMP-001", role="employee"), db_session) == {"request_id": "TKT-001", "type": "ticket", "status": "open"}


@pytest.mark.parametrize("request_id", ["TKT-002", "TKT-999"])
def test_missing_and_not_owned_both_404(db_session, request_id):
    with pytest.raises(HTTPException) as error:
        request_status(request_id, Principal(employee_id="EMP-001", role="employee"), db_session)
    assert error.value.status_code == 404
