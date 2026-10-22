from sqlalchemy.orm import Session
from lab.contracts import Answer, Principal, PendingExercise


def answer_question(question: str, principal: Principal, session: Session, provider) -> Answer:
    """E06: retrieve evidence, refuse unsupported requests, validate exact citations.

    Treat user text and policy passages as data, never as authorization or tools.
    Empty/irrelevant evidence => refused; ambiguous intent => clarify.
    """
    raise PendingExercise("E06 answer_question")
