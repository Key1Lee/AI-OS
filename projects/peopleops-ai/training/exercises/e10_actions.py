from datetime import datetime
from sqlalchemy.orm import Session
from lab.contracts import ActionResult, Confirmation, Plan, Principal, PendingExercise


def prepare_action(plan: Plan, principal: Principal, session: Session, now: datetime) -> dict:
    """E10: stage a 10-minute immutable proposal; no HR/PTO business side effects.

    Return proposal_id, summary, expires_at. Bind proposal to actor and payload hash.
    """
    raise PendingExercise("E10 prepare_action")


def execute_action(confirmation: Confirmation, principal: Principal, session: Session, now: datetime) -> ActionResult:
    """E10: require confirmation, ownership, permission, expiry, payload integrity.

    Lock proposal; atomically persist request, unique receipt, and audit event.
    Exact replay returns the same ID; changed payload/key reuse => HTTP 409.
    """
    raise PendingExercise("E10 execute_action")
