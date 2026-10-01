from __future__ import annotations

from datetime import datetime, timezone

from .models import MasteryState, Mode, Question, Selection
from .persistence import TrainingStore


SIMILARITY_GROUP = {
    "Python semantics": "implementation",
    "Python design": "implementation",
    "Testing strategy": "implementation",
    "Debugging": "implementation",
    "SQL correctness": "data",
    "Data modeling": "data",
    "Distributed systems": "systems",
    "API and integration design": "systems",
    "Reliability": "systems",
    "Incident reasoning": "systems",
    "Delivery and operational readiness": "systems",
    "Communication under ambiguity": "judgment",
    "Decision quality": "judgment",
    "Learning and correction": "judgment",
}


class Selector:
    def __init__(self, store: TrainingStore, questions: tuple[Question, ...]):
        self.store = store
        self.questions = questions

    def select(self, mode: Mode, excluded: set[str] | None = None) -> Selection:
        excluded = excluded or set()
        rows = {row["name"]: row for row in self.store.competency_rows()}
        now = datetime.now(timezone.utc).isoformat()
        last_id = self.store.last_question_id()
        last_competency = self.store.last_competency()
        last_group = SIMILARITY_GROUP.get(last_competency or "")

        def rank(question: Question) -> tuple:
            row = rows[question.competency]
            attempts = self.store.question_attempt_count(question.id)
            due = bool(row["next_review_at"] and row["next_review_at"] <= now)
            unseen = row["state"] == MasteryState.UNSEEN.value
            weak = row["state"] == MasteryState.WEAK.value
            if mode == Mode.WEAKNESS_REVIEW:
                priority = 0 if weak else 5
            elif mode == Mode.COLD_RECALL:
                priority = 0 if due and not unseen else 4 if not unseen else 8
            elif mode == Mode.PRACTICE:
                priority = 0 if weak else 1 if due else 2 if unseen else 3
            else:
                priority = 0 if due else 1 if weak else 2 if unseen else 3
            repeat_penalty = 1 if question.id == last_id else 0
            similarity_penalty = int(
                last_group is not None
                and SIMILARITY_GROUP.get(question.competency) == last_group
            )
            return (
                priority,
                similarity_penalty,
                float(row["mastery"]),
                attempts,
                repeat_penalty,
                question.difficulty,
                question.id,
            )

        candidates = [q for q in self.questions if q.id not in excluded]
        if not candidates:
            candidates = list(self.questions)
        question = min(candidates, key=rank)
        row = rows[question.competency]
        is_cold = mode == Mode.COLD_RECALL or bool(
            row["next_review_at"] and row["next_review_at"] <= now and row["attempts"] > 0
        )
        prior_families = {
            q.family for q in self.questions
            if q.competency == question.competency and self.store.question_attempt_count(q.id) > 0
        }
        is_transfer = bool(prior_families and question.family not in prior_families)
        if row["state"] == MasteryState.UNSEEN.value:
            reason = "untested competency"
        elif row["state"] == MasteryState.WEAK.value:
            reason = "known weakness"
        elif is_cold:
            reason = "scheduled cold recall"
        else:
            reason = "lowest current mastery"
        return Selection(question, reason, is_cold_recall=is_cold, is_transfer=is_transfer)
