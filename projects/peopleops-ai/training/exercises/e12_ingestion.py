from sqlalchemy.orm import Session
from lab.contracts import PendingExercise


def ingest_employees(records: list[dict], session: Session) -> dict:
    """E12: validate entire batch, upsert newer versions in one transaction.

    Return inserted/updated/unchanged counts. Missing source IDs never delete.
    Caller owns commit; failure rolls back batch. Never catch and hide DB errors.
    """
    raise PendingExercise("E12 ingest_employees")
