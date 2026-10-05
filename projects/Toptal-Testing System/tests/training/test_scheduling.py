from datetime import datetime, timedelta, timezone

from training.config import Settings
from training.models import Assistance, Mode, Outcome, Evaluation
import pytest
from training.scheduling import next_review_at


NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)


def settings(tmp_path):
    return Settings(database_path=tmp_path / "training.db")


def test_default_review_intervals(tmp_path):
    config = settings(tmp_path)
    cases = [
        (Outcome.FAIL, Assistance.NONE, Mode.DAILY, False, 1, timedelta(days=1)),
        (Outcome.PASS, Assistance.LIGHT, Mode.PRACTICE, False, 0, timedelta(days=3)),
        (Outcome.PASS, Assistance.NONE, Mode.DAILY, False, 0, timedelta(days=7)),
        (Outcome.PASS, Assistance.NONE, Mode.COLD_RECALL, False, 0, timedelta(days=14)),
        (Outcome.PASS, Assistance.NONE, Mode.DAILY, True, 0, timedelta(days=30)),
    ]
    for outcome, assistance, mode, transfer, failures, expected in cases:
        actual = next_review_at(
            outcome=outcome,
            assistance=assistance,
            mode=mode,
            is_transfer=transfer,
            consecutive_failures=failures,
            settings=config,
            now=NOW,
            evaluation=Evaluation(outcome=outcome, score=1, met=(), missing=(), feedback="synthetic",
                                  evaluation_mode="reasoning", evaluator_provider="mock", evaluator_model="synthetic"),
        )
        assert actual - NOW == expected


def test_repeated_failure_shortens_interval(tmp_path):
    actual = next_review_at(
        outcome=Outcome.FAIL,
        assistance=Assistance.NONE,
        mode=Mode.DAILY,
        is_transfer=False,
        consecutive_failures=2,
        settings=settings(tmp_path),
        now=NOW,
        evaluation=Evaluation(outcome=Outcome.FAIL, score=0, met=(), missing=(), feedback="synthetic",
                              evaluation_mode="reasoning", evaluator_provider="mock", evaluator_model="synthetic"),
    )
    assert actual - NOW == timedelta(hours=12)


@pytest.mark.parametrize("outcome", list(Outcome))
@pytest.mark.parametrize("mode,transfer", [(Mode.DAILY, False), (Mode.COLD_RECALL, False), (Mode.DAILY, True)])
def test_unassessed_coverage_never_uses_success_or_assessed_failure_spacing(tmp_path, outcome, mode, transfer):
    evaluation = Evaluation(outcome=outcome, score=1, met=(), missing=(), feedback="literal coverage")
    actual = next_review_at(outcome=outcome, evaluation=evaluation, assistance=Assistance.NONE,
                            mode=mode, is_transfer=transfer, consecutive_failures=5,
                            settings=settings(tmp_path), now=NOW)
    assert actual == NOW + timedelta(days=1)
