from __future__ import annotations

from .deterministic import enforce_authoritative_results, run_deterministic_checks
from .llm import EvaluationProvider
from .models import Evaluation, Mode, Question
from .persistence import TrainingStore


def evaluate_for_calibration(
    *,
    store: TrainingStore,
    attempt_id: int,
    question: Question,
    answer: str,
    mode: Mode,
    providers: tuple[EvaluationProvider, ...],
) -> tuple[Evaluation, ...]:
    """Evaluate once per explicitly supplied provider and retain separate runs.

    This never averages scores or changes the attempt's primary result/mastery.
    Callers must explicitly construct paid providers; ordinary sessions do not
    invoke this path.
    """
    deterministic = run_deterministic_checks(question, answer)
    results: list[Evaluation] = []
    for provider in providers:
        method = getattr(provider, "evaluate_with_context", None)
        evaluation = (
            method(question, answer, mode, deterministic)
            if method
            else provider.evaluate(question, answer, mode)
        )
        evaluation = enforce_authoritative_results(evaluation, deterministic)
        store.record_calibration_evaluation(
            attempt_id=attempt_id,
            assessment_id=question.id,
            evaluation=evaluation,
        )
        results.append(evaluation)
    return tuple(results)
