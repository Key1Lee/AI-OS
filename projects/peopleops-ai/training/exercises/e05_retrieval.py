from sqlalchemy.orm import Session
from lab.contracts import Principal, PendingExercise


def retrieve(question: str, principal: Principal, session: Session, k: int = 3) -> list[dict]:
    """E05: authorized, current policy sections ranked by pgvector cosine distance.

    Filter audience/retired/effective dates BEFORE top-k. Threshold distance <=0.65.
    Return chunk_id, policy_id, section_id, version, body, distance.
    """
    raise PendingExercise("E05 retrieve")
