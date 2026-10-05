import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lab.contracts import SCENARIO_ID, State
from lab.store import Store

ROOT = Path(__file__).resolve().parents[2]


def cli(state_dir: Path, *arguments: str, input_text: str | None = None):
    return subprocess.run([sys.executable, "-m", "lab", "--state-dir", str(state_dir), *arguments],
                          input=input_text, text=True, capture_output=True, cwd=ROOT,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=90)


def test_guided_nine_step_cli_reaches_local_mastery_and_reset_retains_history(tmp_path):
    # A wrong prediction remains a learning attempt, rather than blocking observation.
    answers = "\n".join(["1000", "ingestion", "idempotency", "duplicate_order_ids",
                          "700 earlier committed orders were appended again during retry.",
                          "upsert", "1000", "order_id", "upsert", ""])
    result = cli(tmp_path, "learn", SCENARIO_ID, input_text=answers)
    assert result.returncode == 0, result.stderr + result.stdout
    headings = ["1 · ORIENT", "2 · PREDICT", "3 · RUN", "4 · OBSERVE", "5 · DIAGNOSE",
                "6 · FIX", "7 · VERIFY", "8 · RECALL", "9 · CONNECT"]
    positions = [result.stdout.index(heading) for heading in headings]
    assert positions == sorted(positions)
    prediction_output = result.stdout[:positions[2]]
    assert "1,700" not in prediction_output and "1700" not in prediction_output
    assert "upsert" not in prediction_output.casefold()
    assert "Actual rows:   1,700" in result.stdout
    assert "Actual rows:   1,000" in result.stdout
    assert "Verification: PASS" in result.stdout
    assert "9 · CONNECT" in result.stdout
    store = Store(tmp_path)
    record, = store.records()
    assert record["state"] == State.MASTERED
    assert record["learning_step"] == 9
    assert record["verification"]["status"] == "PASS"
    assert record["answers"]["predict"][0]["evaluation"]["outcome"] == "fail"
    assert record["answers"]["diagnose"][-1]["evaluation"]["outcome"] == "pass"
    assert record["answers"]["recall"][-1]["evaluation"]["outcome"] == "pass"
    assert "local" in record["mastery_scope"].casefold()
    assert [transition["to"] for transition in record["transitions"]] == [state.value for state in State if state != State.READY]
    evidence = tmp_path / record["run_id"] / "evidence.json"
    evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
    inspected = cli(tmp_path, "inspect", record["run_id"], "--json")
    assert inspected.returncode == 0
    # The command adds its saved-evidence path after its JSON body.
    document, _ = json.JSONDecoder().raw_decode(inspected.stdout)
    assert document["state"] == "MASTERED"
    assert document["verification"]["checks"]["partial_write_retry_safe"]
    reset = cli(tmp_path, "reset", SCENARIO_ID)
    assert reset.returncode == 0, reset.stderr
    records = store.records()
    assert len(records) == 2
    assert records[0]["state"] == State.READY
    assert records[0]["run_id"] != record["run_id"]
    assert store.get(record["run_id"]) == record
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == evidence_hash
    progress = cli(tmp_path, "progress")
    assert progress.returncode == 0
    assert "MASTERED" in progress.stdout and "READY" in progress.stdout
    assert record["run_id"] in progress.stdout and records[0]["run_id"] in progress.stdout


@pytest.mark.parametrize("arguments,message", [
    (("run", "UNKNOWN-SCENARIO"), "Unknown scenario"),
    (("inspect", "missing-run"), "Unknown run"),
    (("lineage", "missing-asset"), "Unknown asset"),
    (("run", SCENARIO_ID, "--fail-after-rows", "1000"), "between 1 and 999"),
])
def test_cli_errors_explain_the_rejected_operation(tmp_path, arguments, message):
    result = cli(tmp_path, *arguments)
    assert result.returncode == 1
    assert "Lab stopped:" in result.stderr
    assert message in result.stderr
    assert "Traceback" not in result.stderr


def test_interrupted_learning_preserves_the_prompt_position_without_disclosing_result(tmp_path):
    result = cli(tmp_path, "learn", SCENARIO_ID, input_text="")
    assert result.returncode == 130
    assert "Session saved" in result.stderr
    assert "--resume RUN_ID" in result.stderr
    assert "1,700" not in result.stdout and "1700" not in result.stdout
    record, = Store(tmp_path).records()
    assert record["state"] == State.READY
    assert record["learning_step"] == 1
    assert record["phases"] == {}
