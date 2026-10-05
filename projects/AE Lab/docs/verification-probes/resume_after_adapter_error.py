"""Inject bridge availability errors; delegate every successful result natively."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.adapters.bridge import AdapterError
from lab.adapters.modeling import NativeModelingAdapter
from lab.adapters.quality import NativeQualityAdapter
from lab.core import Lab
from lab.store import StateError
from lab.warehouse import Warehouse


class FailSecondModeling:
    def __init__(self):
        self.calls = 0
        self.native = NativeModelingAdapter()

    def build(self, *args):
        self.calls += 1
        if self.calls == 2:
            raise AdapterError("Independent probe: modeling runtime became unavailable after fault writes")
        return self.native.build(*args)


class UnavailableQuality:
    def validate(self, *args):
        raise AdapterError("Independent probe: quality runtime unavailable after recovery writes/model")


def main():
    checks = {}
    with tempfile.TemporaryDirectory(prefix="ae-lab-resume-") as temp:
        lab = Lab(Path(temp), modeling=FailSecondModeling())
        try:
            lab.run()
        except AdapterError as exc:
            assert "after fault writes" in str(exc)
        else:
            raise AssertionError("Injected modeling error was hidden")
        interrupted, = lab.store.records()
        run_id = interrupted["run_id"]
        assert interrupted["state"] == "FAULT_INJECTED"
        assert interrupted["verification"] is None
        assert len(Warehouse(lab.directory(interrupted) / "warehouse.sqlite").rows()) == 1700
        assert "baseline" in interrupted["phases"]
        checks["adapter_fault_keeps_resumable_state_and_actual_committed_data"] = True
        resumed = Lab(Path(temp)).run(run_id)
        assert resumed["state"] == "FAILED"
        assert resumed["phases"]["fault"]["rows"] == 1700
        checks["fault_resume_reconstructs_exact_fixture_without_double_append"] = True
        Lab(Path(temp)).answer(run_id, "diagnose", {"layer": "ingestion", "property": "idempotency", "signal": "duplicate_order_ids"})
        broken = Lab(Path(temp), quality=UnavailableQuality())
        try:
            broken.fix(run_id)
        except AdapterError as exc:
            assert "after recovery writes/model" in str(exc)
        else:
            raise AssertionError("Injected recovery error was hidden")
        interrupted = lab.store.get(run_id)
        assert interrupted["state"] == "REMEDIATED" and "recovery" not in interrupted["phases"]
        assert len(Warehouse(lab.directory(interrupted) / "warehouse.sqlite").rows()) == 1000
        try:
            Lab(Path(temp)).verify(run_id)
        except StateError:
            checks["partial_recovery_cannot_be_verified"] = True
        else:
            raise AssertionError("Incomplete recovery substituted for completed native evidence")
        # The advertised guided resume must complete an interrupted repair as well.
        resumed_cli = subprocess.run(
            [sys.executable, "-m", "lab", "--state-dir", temp, "learn", "ORCH-IDEMPOTENCY-001", "--resume", run_id],
            input="upsert\n1000\norder_id\nupsert\n", text=True, capture_output=True,
            cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=90,
        )
        assert resumed_cli.returncode == 0, resumed_cli.stdout + resumed_cli.stderr
        final = lab.store.get(run_id)
        assert final["phases"]["recovery"]["quality_status"] == "PASS"
        assert final["verification"]["status"] == "PASS" and final["learning_step"] == 9
        assert "6 · FIX" in resumed_cli.stdout and "9 · CONNECT" in resumed_cli.stdout
        checks["guided_recovery_resume_finishes_native_checks_verify_recall_connect"] = True
        try:
            Lab(Path(temp), quality=UnavailableQuality()).verify(run_id)
        except AdapterError:
            pass
        else:
            raise AssertionError("Reverification swallowed the unavailable native adapter")
        suspended = lab.store.get(run_id)
        assert suspended["state"] == "REMEDIATED" and suspended["verification"]["status"] == "RUNNING"
        try:
            Lab(Path(temp)).answer(run_id, "recall", {"rows": 1000, "key": "order_id", "repair": "upsert"})
        except StateError:
            checks["reverification_adapter_error_suspends_prior_mastery_and_recall"] = True
        else:
            raise AssertionError("Prior mastery survived unfinished new verification")
        final = Lab(Path(temp)).verify(run_id)
        assert final["verification"]["status"] == "PASS"
        try:
            Lab(Path(temp)).run("unknown-run-id")
        except StateError:
            checks["unknown_run_does_not_silently_start_or_reuse_data"] = True
        else:
            raise AssertionError("Unknown run silently reused an exercise")
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
