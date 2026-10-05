"""Contract checks execute the real sibling evaluator through the bridge."""
import pytest

from lab.adapters.bridge import AdapterError
from lab.adapters.testing import NativeTestingAdapter
from lab.learning import ORIENT, PREDICT, STEPS


@pytest.mark.parametrize("stage,answer", [
    ("predict", {"rows": 1700}),
    ("diagnose", {"layer": "ingestion", "property": "idempotency", "signal": "duplicate_order_ids"}),
    ("recall", {"rows": 1000, "key": "order_id", "repair": "upsert"}),
])
def test_native_evaluation_accepts_declared_correct_answers(stage, answer):
    result = NativeTestingAdapter().evaluate(stage, answer)
    assert result["outcome"] == "pass"
    assert result["score"] == 1
    assert result["provenance"]["interface"] == "training.deterministic.enforce_authoritative_results"
    assert result["provenance"]["source_sha256"]["deterministic.py"]
    assert result["deterministic_results"]["blocking_failures"] == []
    assert "free_text_reasoning" in result["unassessed"]


def test_native_authoritative_failure_overrides_partial_score():
    result = NativeTestingAdapter().evaluate("recall", {"rows": 1700, "key": "order_id", "repair": "upsert"})
    assert result["outcome"] == "fail"
    assert result["score"] <= .39
    assert result["deterministic_results"]["blocking_failures"] == ["rows"]


def test_terminology_in_prose_cannot_earn_objective_credit():
    answer = {"reason": "ingestion idempotency duplicate_order_ids order_id upsert 1000"}
    result = NativeTestingAdapter().evaluate("diagnose", answer)
    assert result["outcome"] == "fail"
    assert result["score"] == 0
    assert result["answer"] == answer


def test_declared_equivalents_and_strict_row_types():
    result = NativeTestingAdapter().evaluate("diagnose", {"layer": "loader", "property": "retry safety", "signal": "duplicate order ids"})
    assert result["outcome"] == "pass"
    result = NativeTestingAdapter().evaluate("predict", {"rows": "1700"})
    assert result["outcome"] == "fail"


def test_missing_runtime_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("AE_LAB_TESTING_ROOT", str(tmp_path / "missing"))
    monkeypatch.delenv("AE_LAB_TESTING_PYTHON", raising=False)
    with pytest.raises(AdapterError, match="native runtime or bridge missing"):
        NativeTestingAdapter().evaluate("predict", {"rows": 1700})


def test_learning_order_and_prediction_do_not_disclose_answer():
    assert STEPS == ("orient", "predict", "run", "observe", "diagnose", "fix", "verify", "recall", "connect")
    assert "1700" not in PREDICT and "1,700" not in PREDICT
    assert "upsert" not in ORIENT.casefold() and "idempotency" not in ORIENT.casefold()
