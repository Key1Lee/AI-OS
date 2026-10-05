"""Run original Toptal contracts inside its runtime; write no learner records."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

# The bridge reads sibling sources without writing adjacent Python cache files.
sys.dont_write_bytecode = True

import training
from training.deterministic import (
    DeterministicCheck,
    DeterministicReport,
    enforce_authoritative_results,
    run_deterministic_checks,
)
from training.models import Criterion, Evaluation, Outcome, Question

POLICY_VERSION = "ae-lab-idempotency-objective-v1"

CONTRACTS = {
    "predict": {
        "prompt": "Predict the warehouse row count after a partial insert and full retry.",
        "criteria": (("rows", "Predicted row count follows the recorded retry contract."),),
    },
    "diagnose": {
        "prompt": "Identify the first corrupting layer, missing property and quality evidence.",
        "criteria": (
            ("layer", "Diagnosis identifies the layer that performs repeated writes."),
            ("property", "Diagnosis identifies the missing safe-repetition property."),
            ("signal", "Diagnosis cites the recorded duplicate order-key signal."),
        ),
    },
    "recall": {
        "prompt": "Recall the safe rerun result, stable order identity and repair operation.",
        "criteria": (
            ("rows", "Recall predicts a stable recovered row count after another load."),
            ("key", "Recall selects a stable source order identity."),
            ("repair", "Recall identifies an update-or-insert operation."),
        ),
    },
}


def exact_string(value: object, allowed: set[str]) -> bool:
    """Accept declared equivalents only; never match words in an explanation."""
    return isinstance(value, str) and value.strip().casefold() in allowed


def checks_for(stage: str, answer: dict) -> dict[str, bool]:
    if stage == "predict":
        return {"rows": type(answer.get("rows")) is int and answer["rows"] == 1700}
    if stage == "diagnose":
        return {
            "layer": exact_string(answer.get("layer"), {"ingestion", "loader", "loading", "orchestration"}),
            "property": exact_string(answer.get("property"), {"idempotency", "retry_safety", "retry safety", "idempotent_writes", "idempotent writes"}),
            "signal": exact_string(answer.get("signal"), {"duplicate_order_ids", "duplicate order ids", "duplicate_order_keys", "duplicate order keys"}),
        }
    return {
        "rows": type(answer.get("rows")) is int and answer["rows"] == 1000,
        "key": exact_string(answer.get("key"), {"order_id", "order id"}),
        "repair": exact_string(answer.get("repair"), {"upsert", "merge", "merge_upsert", "merge/upsert"}),
    }


def evaluate(stage: str, answer: dict) -> dict:
    if stage not in CONTRACTS or not isinstance(answer, dict):
        raise ValueError("Evaluation requires a known learning stage and structured answer.")
    contract = CONTRACTS[stage]
    question = Question(
        id=f"ORCH-IDEMPOTENCY-001:{stage}:v1",
        competency="Reliability: idempotent ingestion",
        family="partial-write-and-retry",
        difficulty=3,
        prompt=contract["prompt"],
        criteria=tuple(Criterion(key, description, ()) for key, description in contract["criteria"]),
        hints=(),
        followups={},
        source="AE Lab authored original deterministic scenario",
    )
    serialized = json.dumps(answer, sort_keys=True, allow_nan=False)
    native = run_deterministic_checks(question, serialized)
    results = checks_for(stage, answer)
    objective = tuple(
        DeterministicCheck(key, results[key], True, description)
        for key, description in contract["criteria"]
    )
    report = DeterministicReport(POLICY_VERSION, (*native.checks, *objective))
    passed = all(results.values())
    evaluation = Evaluation(
        outcome=Outcome.PASS if passed else Outcome.FAIL,
        score=round(sum(results.values()) / len(results), 3),
        met=tuple(key for key, ok in results.items() if ok),
        missing=tuple(key for key, ok in results.items() if not ok),
        feedback="Structured checks passed." if passed else "Recheck the selections against the scenario evidence.",
        evaluator="ae-lab-objective-checks+toptal-authoritative-enforcement",
        evaluator_provider="native_toptal_deterministic",
        evaluator_model="none",
        evaluation_mode="structured_objective",
        evaluation_confidence="high_for_declared_fields_only",
        rubric_version=POLICY_VERSION,
        evidence=tuple(f"{key}={json.dumps(answer.get(key))}" for key in results),
        raw={"question_id": question.id, "answer": answer},
    )
    enforced = enforce_authoritative_results(evaluation, report)
    source_files = [Path(training.__file__).parent / name for name in ("models.py", "deterministic.py")]
    provenance = {
        "system": "Toptal-Testing System",
        "native_version": training.__version__,
        "interface": "training.deterministic.enforce_authoritative_results",
        "question_id": question.id,
        "policy_version": POLICY_VERSION,
        "source_files": [str(path) for path in source_files],
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        "provider": enforced.evaluator_provider,
        "mode": enforced.evaluation_mode,
    }
    return {
        "outcome": enforced.outcome.value,
        "score": enforced.score,
        "checks": [asdict(check) for check in report.checks],
        "feedback": enforced.feedback,
        "provenance": provenance,
        "limited_scope": "Exact authored answer fields for this scenario; free-text reasoning and broader engineering mastery are unassessed.",
        "answer": answer,
        "unassessed": ["free_text_reasoning", "canonical_mastery", "transfer_to_other_scenarios"],
        "deterministic_results": enforced.deterministic_results,
    }


if __name__ == "__main__":
    request = json.load(sys.stdin)
    print(json.dumps(evaluate(request["stage"], request["answer"]), allow_nan=False))
