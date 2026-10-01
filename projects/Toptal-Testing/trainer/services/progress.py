from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from trainer.mastery.policy import advance, stamp
from trainer.repositories.models import AttemptRow, EventRow, MasteryRow, MistakeRow
from trainer.schemas.models import Exercise


def add_event(session: Session, attempt_id: str, name: str, payload: dict, now: datetime):
    session.add(EventRow(id=uuid4().hex, attempt_id=attempt_id, event_type=name, created_at=stamp(now), payload=payload))


def record_progress(session: Session, attempt: AttemptRow, exercise: Exercise, result: dict, independent: bool, now: datetime) -> list[dict]:
    updates = []
    execution_failures = {"runtime","timeout","policy","limit"}
    no_result_evidence = all(c["reason"] in execution_failures for c in result["categories"])
    for competency in exercise.competencies:
        if no_result_evidence and competency != "sql.execution":
            # A query that never runs does not test joins, NULL reasoning, grain,
            # retention, etc. Preserve those states as unknown or demonstrated.
            continue
        if competency == "sql.execution":
            tests = [{**c,"passed":c["reason"] not in execution_failures} for c in result["categories"]]
        else:
            tests = [c for c in result["categories"] if competency in c["competencies"]]
        if not tests:
            continue
        passed = all(c["passed"] for c in tests)
        mistakes = list(session.scalars(select(MistakeRow).where(MistakeRow.competency_id == competency)))
        seen = set()
        for test in tests:
            if test["passed"]:
                continue
            category = f"execution:{test['reason']}" if test["reason"] in {"runtime", "timeout", "policy", "limit"} else f"contract:{test['id']}"
            if category in seen:
                continue
            seen.add(category)
            mistake = next((m for m in mistakes if m.category == category), None)
            if mistake is None:
                mistake = MistakeRow(id=uuid4().hex, competency_id=competency, category=category, state={
                    "first_occurrence": stamp(now), "recurrence_count": 0, "source_attempts": [],
                    "exercise_ids": [], "families": [], "resolved_evidence": [],
                    "detection_type": "deterministic", "severity": "major",
                    "classification": "Implementation Error" if competency == "sql.execution" else "Test Contract Failure",
                })
                session.add(mistake)
                mistakes.append(mistake)
            state = dict(mistake.state)
            state.update(last_occurrence=stamp(now), recurrence_count=state["recurrence_count"] + 1,
                         status="OPEN", label=test["category"], diagnostic=test["feedback"],
                         next_retest=stamp(now + timedelta(days=1)))
            state["source_attempts"] = [*state["source_attempts"], attempt.id]
            state["exercise_ids"] = sorted(set(state["exercise_ids"] + [exercise.id]))
            state["families"] = sorted(set(state["families"] + [exercise.family]))
            mistake.state = state
            add_event(session, attempt.id, "mistake_detected", {"mistake_id": mistake.id, "competency_id": competency, "category": category}, now)
        if independent and passed:
            for mistake in mistakes:
                if mistake.state["status"] == "OPEN" and exercise.family not in mistake.state["families"]:
                    state = dict(mistake.state)
                    state.update(status="VERIFIED_CLOSED", next_retest=None)
                    state["resolved_evidence"] = [*state["resolved_evidence"], dict(attempt_id=attempt.id, exercise_id=exercise.id, at=stamp(now), basis="Independent full-suite success in a different exercise family.")]
                    mistake.state = state
                    add_event(session, attempt.id, "mistake_retested", {"mistake_id": mistake.id}, now)
        unresolved = sum(m.state["status"] == "OPEN" for m in mistakes)
        row = session.get(MasteryRow, competency)
        old = row.state
        evidence = dict(attempt_id=attempt.id, exercise_id=exercise.id, family=exercise.family,
                        difficulty=exercise.difficulty, passed=passed,
                        independent=independent, hints=attempt.hint_count,
                        solution_seen=attempt.solution_seen, external_assistance=attempt.external_assistance)
        row.state = advance(old, evidence, unresolved, now)
        add_event(session, attempt.id, "competency_evidence_added", {"competency_id": competency, "evidence": evidence}, now)
        add_event(session, attempt.id, "review_scheduled", {"competency_id": competency, "next_review": row.state["next_review"]}, now)
        if row.state["level"] != old["level"]:
            add_event(session, attempt.id, "mastery_changed", {"competency_id": competency, "before": old["level"], "after": row.state["level"], "policy_version": row.state["policy_version"]}, now)
        updates.append({"competency_id": competency, "before": old["label"], "after": row.state["label"], "independent_successes": len(row.state["independent_successes"]), "next_review": row.state["next_review"]})
    return updates
