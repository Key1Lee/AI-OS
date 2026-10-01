from __future__ import annotations

from dataclasses import dataclass

from .models import Assistance, MasteryState, Mode, Outcome


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
