from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from lab.models import Ticket, PTORequest
from lab.contracts import Confirmation, Plan, Principal
from exercises.e10_actions import prepare_action, execute_action

pytestmark = pytest.mark.database
ACTOR = Principal(employee_id="EMP-001", role="employee")
NOW = datetime(2026,10,1,tzinfo=timezone.utc)
PLAN = Plan(tool="create_ticket", arguments={"employee_id": "EMP-001", "category": "Payroll", "subject": "Missing pay"}, summary="Prepare Payroll ticket")


def test_preview_has_no_ticket_side_effect(db_session):
    before = db_session.scalar(select(func.count()).select_from(Ticket))
    proposal = prepare_action(PLAN, ACTOR, db_session, NOW)
    assert proposal["proposal_id"]
    assert db_session.scalar(select(func.count()).select_from(Ticket)) == before


def test_confirmation_replay_creates_one_ticket(db_session):
    before = db_session.scalar(select(func.count()).select_from(Ticket))
    proposal = prepare_action(PLAN, ACTOR, db_session, NOW)
    confirmation = Confirmation(proposal_id=proposal["proposal_id"], confirmed=True, idempotency_key="payroll-test-key")
    first = execute_action(confirmation, ACTOR, db_session, NOW)
    second = execute_action(confirmation, ACTOR, db_session, NOW)
    assert first.request_id == second.request_id and second.replayed
    assert db_session.scalar(select(func.count()).select_from(Ticket)) == before + 1


@pytest.mark.parametrize("confirmed,actor,now,expected", [
    (False, ACTOR, NOW, 400), (True, Principal(employee_id="EMP-002", role="employee"), NOW, 404),
    (True, ACTOR, NOW + timedelta(minutes=11), 409)])
def test_invalid_confirmation_has_no_side_effect(db_session, confirmed, actor, now, expected):
    proposal = prepare_action(PLAN, ACTOR, db_session, NOW)
    before = db_session.scalar(select(func.count()).select_from(Ticket))
    with pytest.raises(HTTPException) as error:
        execute_action(Confirmation(proposal_id=proposal["proposal_id"], confirmed=confirmed, idempotency_key="payroll-test-key"), actor, db_session, now)
    assert error.value.status_code == expected
    assert db_session.scalar(select(func.count()).select_from(Ticket)) == before


def test_pto_requires_valid_balance_and_dates(db_session):
    plan = Plan(tool="create_pto", arguments={"employee_id": "EMP-001", "start_date": "2026-10-15", "end_date": "2026-10-16", "hours": 16}, summary="Request 16 hours PTO")
    proposal = prepare_action(plan, ACTOR, db_session, NOW)
    result = execute_action(Confirmation(proposal_id=proposal["proposal_id"], confirmed=True, idempotency_key="pto-test-key"), ACTOR, db_session, NOW)
    row = db_session.get(PTORequest, result.request_id)
    assert row.hours == 16 and row.employee_id == "EMP-001" and row.status == "pending"
