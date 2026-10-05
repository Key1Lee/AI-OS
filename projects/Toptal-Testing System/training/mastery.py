from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .models import Assistance, Evaluation, MasteryState, Mode, Outcome


CREDIT_POLICY_VERSION = "assessed-evidence-v1"


@dataclass(frozen=True)
class AssessmentEligibility:
    assessed: bool
    reason: str
    authoritative_failure: bool = False


def assessment_eligibility(
    evaluation: Evaluation | Mapping[str, Any] | None,
) -> AssessmentEligibility:
    """Distinguish an assessment from literal coverage, including saved results.

    Confidence does not turn coverage into assessment, or introduce a new cutoff
    for the existing structured reasoning evaluator. Stored eligibility flags
    are advisory: derive the decision from the original evaluator metadata.
    """
    def value(name: str, default=None):
        if isinstance(evaluation, Mapping):
            return evaluation.get(name, default)
        return getattr(evaluation, name, default)

    deterministic = value("deterministic_results", {})
    checks = deterministic.get("checks", ()) if isinstance(deterministic, Mapping) else ()
    if isinstance(checks, (list, tuple)) and any(
        isinstance(check, Mapping)
        and check.get("authoritative") is True
        and check.get("passed") is False
        for check in checks
    ):
        return AssessmentEligibility(True, "authoritative_deterministic_failure", True)
    mode = value("evaluation_mode")
    metadata = [value(name) for name in ("evaluator_provider", "evaluator_model", "rubric_version")]
    complete = all(isinstance(item, str) and item.strip() and item != "unknown" for item in metadata)
    if mode == "reasoning" and complete and metadata[0] != "offline_fallback":
        return AssessmentEligibility(True, "structured_reasoning")
    return AssessmentEligibility(False, "lexical_coverage" if mode == "lexical_conservative" else "missing_or_unknown_evaluator_metadata")


def assessment_outcome(
    evaluation: Evaluation | Mapping[str, Any] | None, outcome: Outcome | str | None,
) -> Outcome | None:
    eligibility = assessment_eligibility(evaluation)
    if eligibility.authoritative_failure:
        return Outcome.FAIL
    if not eligibility.assessed:
        return None
    try:
        return Outcome(outcome)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class MasteryEvidence:
    attempts: int
    independent_successes: int
    hinted_successes: int
    failures: int
    cold_recall_successes: int
    transfer_successes: int
    distinct_families: int
    consecutive_failures: int


def score_delta(
    outcome: Outcome, assistance: Assistance, mode: Mode, is_transfer: bool
) -> float:
    if outcome == Outcome.FAIL:
        return -0.12
    if outcome == Outcome.PARTIAL:
        return -0.03 if assistance == Assistance.NONE else -0.06
    if assistance != Assistance.NONE:
        return 0.04
    if is_transfer:
        return 0.20
    if mode == Mode.COLD_RECALL:
        return 0.15
    return 0.12


def updated_score(current: float, delta: float) -> float:
    return round(min(1.0, max(0.0, current + delta)), 3)


def classify(score: float, evidence: MasteryEvidence) -> MasteryState:
    if evidence.attempts == 0:
        return MasteryState.UNSEEN
    if evidence.consecutive_failures >= 2 or (
        evidence.failures > 0 and evidence.independent_successes == 0 and score < 0.25
    ):
        return MasteryState.WEAK
    if score < 0.40:
        return MasteryState.LEARNING
    if score < 0.65:
        return MasteryState.DEVELOPING
    mastered = (
        score >= 0.85
        and evidence.attempts >= 5
        and evidence.independent_successes >= 3
        and evidence.cold_recall_successes >= 1
        and evidence.transfer_successes >= 1
        and evidence.distinct_families >= 3
    )
    return MasteryState.MASTERED if mastered else MasteryState.RELIABLE
