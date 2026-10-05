from training.mastery import MasteryEvidence, classify, score_delta, updated_score
from training.models import Assistance, MasteryState, Mode, Outcome
from training.mastery import assessment_eligibility, assessment_outcome
import pytest


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


def reasoning_metadata(**changes):
    return {"evaluation_mode": "reasoning", "evaluator_provider": "mock-reasoning",
            "evaluator_model": "synthetic-model", "rubric_version": "senior-evaluator-v1",
            "evaluation_confidence": "low", **changes}


def test_reasoning_keeps_existing_policy_without_confidence_cutoff():
    metadata = reasoning_metadata()
    assert assessment_eligibility(metadata).assessed
    assert assessment_outcome(metadata, "pass") == Outcome.PASS


@pytest.mark.parametrize("change", [
    {"evaluation_mode": "lexical_conservative"}, {"evaluation_mode": "new-unknown-mode"},
    {"evaluation_mode": None}, {"evaluator_provider": ""}, {"evaluator_provider": "offline_fallback"},
    {"evaluator_model": "unknown"}, {"rubric_version": None},
])
def test_coverage_or_incomplete_metadata_cannot_claim_assessed_success(change):
    metadata = reasoning_metadata(**change, assessment_eligible=True)
    assert not assessment_eligibility(metadata).assessed
    assert assessment_outcome(metadata, "pass") is None


def test_only_real_authoritative_failure_overrides_coverage():
    metadata = {"evaluation_mode": "lexical_conservative", "deterministic_results": {
        "checks": [{"name": "answer_present", "authoritative": True, "passed": False}],
    }}
    assert assessment_eligibility(metadata).authoritative_failure
    assert assessment_outcome(metadata, "pass") == Outcome.FAIL
    metadata["deterministic_results"]["checks"][0]["passed"] = True
    assert assessment_outcome(metadata, "pass") is None
    metadata["deterministic_results"]["checks"][0].update(passed="false", authoritative="true")
    assert assessment_outcome(metadata, "pass") is None
