from training.mastery import MasteryEvidence, classify, score_delta, updated_score
from training.models import Assistance, MasteryState, Mode, Outcome


def evidence(**overrides) -> MasteryEvidence:
    values = dict(
        attempts=5,
        independent_successes=3,
        hinted_successes=0,
        failures=0,
        cold_recall_successes=1,
        transfer_successes=1,
        distinct_families=3,
        consecutive_failures=0,
    )
    values.update(overrides)
    return MasteryEvidence(**values)


def test_mastered_requires_multiple_independent_cold_and_transfer_evidence():
    assert classify(0.90, evidence()) == MasteryState.MASTERED
    assert classify(0.90, evidence(cold_recall_successes=0)) == MasteryState.RELIABLE
    assert classify(0.90, evidence(transfer_successes=0)) == MasteryState.RELIABLE
    assert classify(0.90, evidence(independent_successes=2)) == MasteryState.RELIABLE


def test_hint_credit_is_smaller_and_scores_are_bounded():
    hinted = score_delta(Outcome.PASS, Assistance.LIGHT, Mode.PRACTICE, False)
    independent = score_delta(Outcome.PASS, Assistance.NONE, Mode.PRACTICE, False)
    transfer = score_delta(Outcome.PASS, Assistance.NONE, Mode.PRACTICE, True)
    assert 0 < hinted < independent < transfer
    assert updated_score(0.99, transfer) == 1.0
    assert updated_score(0.01, -0.12) == 0.0


def test_one_independent_success_is_learning_not_mastery():
    state = classify(
        0.12,
        evidence(
            attempts=1,
            independent_successes=1,
            cold_recall_successes=0,
            transfer_successes=0,
            distinct_families=1,
        ),
    )
    assert state == MasteryState.LEARNING
