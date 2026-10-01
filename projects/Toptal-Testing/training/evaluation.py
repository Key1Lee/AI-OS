from __future__ import annotations

import re

from .deterministic import DeterministicReport, run_deterministic_checks
from .models import Evaluation, Outcome, Question


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def evaluate_deterministically(
    question: Question,
    answer: str,
    deterministic: DeterministicReport | None = None,
    fallback_reason: str | None = None,
) -> Evaluation:
    """Conservative, transparent fallback; never claims semantic understanding."""
    text = _normalise(answer)
    met: list[str] = []
    missing: list[str] = []
    earned = 0.0
    possible = 0.0
    for criterion in question.criteria:
        possible += criterion.weight
        if any(term in text for term in criterion.any_of):
            met.append(criterion.id)
            earned += criterion.weight
        else:
            missing.append(criterion.id)
    score = round(earned / possible if possible else 0.0, 3)
    if score >= 0.75:
        outcome = Outcome.PASS
    elif score >= 0.45:
        outcome = Outcome.PARTIAL
    else:
        outcome = Outcome.FAIL
    descriptions = {criterion.id: criterion.description for criterion in question.criteria}
    if missing:
        feedback = "Missing or insufficiently explicit: " + "; ".join(
            descriptions[item] for item in missing
        )
    else:
        feedback = "All explicit rubric dimensions were addressed."
    misconception = None
    if outcome == Outcome.FAIL:
        misconception = "Omitted core dimensions: " + ", ".join(missing)
    report = deterministic or run_deterministic_checks(question, answer)
    dimension_score = round(score * 100)
    return Evaluation(
        outcome=outcome,
        score=score,
        met=tuple(met),
        missing=tuple(missing),
        feedback=feedback,
        misconception=misconception,
        evaluator="offline_fallback:deterministic-rubric-v1:lexical_conservative",
        evaluator_provider="offline_fallback",
        evaluator_model="deterministic-rubric-v1",
        evaluation_mode="lexical_conservative",
        evaluation_confidence="low",
        dimension_scores={
            "correctness": dimension_score,
            "reasoning": dimension_score,
            "completeness": dimension_score,
            "engineering_judgment": dimension_score,
            "communication": dimension_score,
            "production_awareness": dimension_score,
        },
        weaknesses=tuple(descriptions[item] for item in missing),
        missed_concepts=tuple(missing),
        deterministic_results=report.as_dict(),
        fallback_reason=fallback_reason,
        raw={"method": "literal rubric evidence", "answer_length": len(answer)},
    )
