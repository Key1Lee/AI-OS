from sqlalchemy.orm import Session
from lab.contracts import Principal, PendingExercise


def request_status(request_id: str, principal: Principal, session: Session) -> dict:
    """E13: own PTO/ticket or HR. Unauthorized and missing IDs both return 404.

    Return request_id, type ('pto'/'ticket'), status; no private descriptions.
    """
    raise PendingExercise("E13 request_status")
