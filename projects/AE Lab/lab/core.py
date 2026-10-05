from __future__ import annotations

import json
import hashlib
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from .adapters.modeling import NativeModelingAdapter
from .adapters.orchestration import NativeOrchestrationAdapter
from .adapters.quality import NativeQualityAdapter
from .adapters.observability import NativeObservabilityAdapter
from .adapters.testing import NativeTestingAdapter
from .contracts import CONTRACT_VERSION, SCENARIO_ID, EventType, State
from .fixtures import commerce, revenue
from .store import Store, StateError
from .telemetry import emit, export, openlineage
from .warehouse import Warehouse


def publication_decision(schedule, model, quality, source, loaded, materialized) -> dict:
    """Compose this phase's native evidence; a scoped Quality gate is not full trust."""
    schedule = schedule if isinstance(schedule, dict) else {}
    model = model if isinstance(model, dict) else {}
    quality = quality if isinstance(quality, dict) else {}
    expected_count = len(source)
    checks = {
        "execution_complete": schedule.get("status") == "SUCCESS",
        "model_correctness": model.get("status") == "PASS",
        "quality_gate": quality.get("status") == "PASS" and quality.get("gate_open") is True,
        "complete_row_coverage": expected_count > 0 and len(loaded) == len(materialized) == expected_count
            and all(type(count) is int and count == expected_count for count in (
                model.get("row_count"), quality.get("total_rows"), quality.get("validated_rows"),
                quality.get("distinct_keys"))) and quality.get("duplicate_extra") == 0,
    }
    try:
        certified = model.get("rows")
        checks["materialized_output_matches_model"] = isinstance(certified, list) and (
            Counter(json.dumps(row, sort_keys=True) for row in certified)
            == Counter(json.dumps(row, sort_keys=True) for row in materialized))
    except (TypeError, ValueError):
        checks["materialized_output_matches_model"] = False
    try:
        observed = Decimal(str(model.get("revenue")))
        checks["revenue_reconciled"] = observed.is_finite() and observed == Decimal(revenue(source)) == Decimal(revenue(materialized))
    except (InvalidOperation, ValueError, TypeError, KeyError):
        checks["revenue_reconciled"] = False
    reasons = [name for name, passed in checks.items() if not passed]
    return {"trusted": not reasons, "rejection_reasons": reasons}


class Lab:
    def __init__(self, root: Path, *, modeling=None, orchestration=None, quality=None, observability=None, testing=None):
        self.store = Store(root)
        self.modeling = modeling or NativeModelingAdapter()
        self.orchestration = orchestration or NativeOrchestrationAdapter()
        self.quality = quality or NativeQualityAdapter()
        self.observability = observability or NativeObservabilityAdapter()
        self.testing = testing or NativeTestingAdapter()

    def directory(self, record: dict) -> Path:
        return self.store.root / record["run_id"]

    def save(self, record: dict):
        self.store.save(record)
        export(record, self.directory(record))
        (self.directory(record) / "openlineage.json").write_text(json.dumps(openlineage(record), indent=2) + "\n")

    def start(self, seed: int = 42, fail_after_rows: int = 700) -> dict:
        if type(fail_after_rows) is not int or not 1 <= fail_after_rows < 1000:
            raise ValueError("fail_after_rows must be an integer between 1 and 999")
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        record = {"contract_version": CONTRACT_VERSION, "run_id": str(uuid4()), "scenario_id": SCENARIO_ID,
                  "created_at": datetime.now(timezone.utc).isoformat(), "state": State.READY.value,
                  "seed": seed, "fail_after_rows": fail_after_rows, "policy": "append", "learning_step": 0,
                  "transitions": [], "events": [], "phases": {}, "answers": {}, "verification": None, "active_incidents": {},
                  "assistance": {"automated_demo": False, "exposure": "guided and repeated exposure; transfer unassessed"},
                  "mastery_scope": "Local objective idempotency exercise only; guided/repeated evidence, prose and broad competency unassessed"}
        directory = self.directory(record)
        directory.mkdir()
        fixture_text = json.dumps(commerce(seed), indent=2) + "\n"
        (directory / "fixtures.json").write_text(fixture_text)
        record["fixture_sha256"] = hashlib.sha256(fixture_text.encode()).hexdigest()
        emit(record, "lab", None, EventType.RUN_STARTED, "RUNNING", {"virtual_time": True, "seed": seed})
        self.save(record)
        return record

    def source(self, record: dict) -> list[dict]:
        fixture_text = (self.directory(record) / "fixtures.json").read_text()
        fingerprint = record.get("fixture_sha256") or hashlib.sha256((json.dumps(commerce(record["seed"]), indent=2) + "\n").encode()).hexdigest()
        if hashlib.sha256(fixture_text.encode()).hexdigest() != fingerprint:
            raise StateError("Pinned source fixture changed; reset to create a new deterministic exercise")
        return json.loads(fixture_text)["orders"]

    def phase(self, record: dict, name: str, warehouse: Warehouse, policy: str, crash: int | None) -> dict:
        source = self.source(record)
        schedule = self.orchestration.schedule(f"{record['run_id']}:{name}", crash)
        if schedule["status"] != "SUCCESS":
            raise RuntimeError("Native orchestration did not complete the declared load")
        if policy == "upsert":
            warehouse.enable_upsert()
        attempts = []
        for attempt in schedule["attempts"]:
            if attempt["status"] == "FAILED":
                if crash is None or attempt["error"]["type"] != "transient":
                    raise RuntimeError("Unexpected native failure; no undeclared writes allowed")
                warehouse.write(source[:crash], policy)
                committed = len(warehouse.rows())
                emit(record, "orchestration", "orders_raw", EventType.RUN_RETRIED, "RETRYING",
                     {"phase": name, "committed_rows": committed, "attempt": attempt, "failure_after_rows": crash})
            elif attempt["status"] == "SUCCESS":
                warehouse.write(source, policy)
                committed = len(warehouse.rows())
            else:
                raise RuntimeError("Incomplete native attempt")
            attempts.append({"native": attempt, "warehouse_rows_after_attempt": committed})
        loaded = warehouse.rows()
        emit(record, "orchestration", "orders_raw", EventType.ASSET_MATERIALIZED, "SUCCESS",
             {"phase": name, "row_count": len(loaded), "policy": policy})
        model = self.modeling.build(loaded, source, record["run_id"])
        warehouse.materialize(model["rows"])
        emit(record, "modeling", "fct_orders", EventType.MODEL_COMPLETED if model["status"] == "PASS" else EventType.MODEL_FAILED,
             model["status"], {"phase": name, "row_count": model["row_count"], "revenue": model["revenue"], "sql": model["sql"]})
        timestamp = record["events"][-1]["timestamp"]
        quality = self.quality.validate(warehouse.rows("fct_orders"), record["run_id"], timestamp)
        emit(record, "quality", "fct_orders", EventType.QUALITY_CHECK_PASSED if quality["status"] == "PASS" else EventType.QUALITY_CHECK_FAILED,
             quality["status"], {"phase": name, "duplicate_extra": quality["duplicate_extra"], "gate_open": quality["gate_open"]})
        measurements = {"run_id": record["run_id"], "scenario_id": SCENARIO_ID, "timestamp": timestamp,
                        "phase": name, "rows": len(loaded), "expected_rows": len(source),
                        "duplicate_extra": quality["duplicate_extra"],
                        "revenue": int(Decimal(model["revenue"]) * 100), "expected_revenue": int(Decimal(revenue(source)) * 100),
                        "measurement_unit": "USD cents", "quality_status": quality["status"], "model_status": model["status"],
                        "model_sql": model["sql"], "quality_events": quality["events"]}
        observability = self.observability.observe(measurements, str(self.directory(record) / "observability.sqlite"))
        active = record.setdefault("active_incidents", {})
        observed = {incident["id"] for incident in observability["incidents"]}
        for incident_id in sorted(observed - set(active)):
            incident_key = f"{record['run_id']}:{incident_id}:{len(record['events']) + 1}"
            emit(record, "observability", "executive_dashboard", EventType.INCIDENT_OPENED, "FAILED",
                 {"phase": name, "incident_key": incident_key, "native_incident_id": incident_id,
                  "snapshot_id": observability["snapshot_id"], "impact": observability["impact"]})
            active[incident_id] = {"incident_key": incident_key, "opened_event_id": record["events"][-1]["event_id"]}
        for incident_id in sorted(set(active) - observed):
            emit(record, "observability", "executive_dashboard", EventType.INCIDENT_RESOLVED, "HEALTHY",
                 {"phase": name, "native_incident_id": incident_id, **active.pop(incident_id),
                  "snapshot_id": observability["snapshot_id"]})
        emit(record, "observability", "observability.snapshot", EventType.ASSET_MATERIALIZED,
             "FAILED" if observed else "HEALTHY", {"phase": name, "snapshot_id": observability["snapshot_id"],
                                                    "consumer": "executive_dashboard", "actual_artifact": "native observability snapshot"})
        publication = publication_decision(schedule, model, quality, source, loaded, warehouse.rows("fct_orders"))
        result = {"rows": len(loaded), "expected_rows": len(source), "revenue": model["revenue"],
                  "expected_revenue": revenue(source), "duplicate_extra": quality["duplicate_extra"],
                  "pipeline_status": schedule["status"], "quality_status": quality["status"], "model_status": model["status"],
                  "freshness": "NOT_MEASURED", "publication": "ELIGIBLE" if publication["trusted"] else "BLOCKED",
                  "publication_rejections": publication["rejection_reasons"],
                  "dashboard": {"potential_revenue": model["revenue"], "trusted": publication["trusted"]},
                  "attempts": attempts, "orchestration": schedule, "modeling": model,
                  "quality": quality, "observability": observability}
        record["phases"][name] = result
        self.save(record)
        return result

    def run(self, run_id: str | None = None, *, seed: int = 42, fail_after_rows: int = 700) -> dict:
        record = self.store.get(run_id) if run_id else self.start(seed, fail_after_rows)
        if record["state"] == State.READY:
            baseline = Warehouse(self.directory(record) / "baseline.sqlite")
            # Baseline may be retried after an adapter error, so replacement uses safe writes.
            result = self.phase(record, "baseline", baseline, "upsert", None)
            if not (result["rows"] == 1000 and result["quality_status"] == "PASS" and result["model_status"] == "PASS"):
                raise RuntimeError("Baseline assertions failed; fault execution stopped")
            self.store.transition(record, State.BASELINE)
        if record["state"] == State.BASELINE:
            self.store.transition(record, State.FAULT_INJECTED)
        if record["state"] == State.FAULT_INJECTED:
            warehouse = Warehouse(self.directory(record) / "warehouse.sqlite")
            # Reconstruct the deterministic fault from empty Lab state after interruption.
            with warehouse.connect() as db:
                db.execute("DELETE FROM orders_raw")
            result = self.phase(record, "fault", warehouse, "append", record["fail_after_rows"])
            if not (result["rows"] == 1000 + record["fail_after_rows"] and result["duplicate_extra"] == record["fail_after_rows"]
                    and result["quality_status"] == "FAIL" and result["observability"]["incidents"]):
                raise RuntimeError("Injected scenario did not produce its declared failure")
            self.store.transition(record, State.FAILED)
            self.save(record)
        elif record["state"] not in {State.FAILED, State.DIAGNOSING, State.REMEDIATED, State.VERIFIED, State.MASTERED}:
            raise StateError(f"Cannot execute scenario from {record['state']}")
        return record

    def answer(self, run_id: str, stage: str, answer: dict) -> dict:
        record = self.store.get(run_id)
        if stage not in {"predict", "diagnose", "recall"}:
            raise ValueError("Unknown learning stage")
        if stage == "predict" and record["fail_after_rows"] != 700:
            raise StateError("Guided prediction uses the authored 700-row crash; alternate faults are execution experiments")
        required = {"predict": {State.READY}, "diagnose": {State.FAILED, State.DIAGNOSING},
                    "recall": {State.VERIFIED}}[stage]
        if record["state"] not in required:
            raise StateError(f"{stage} unavailable from {record['state']}")
        if stage == "recall" and (not record["verification"] or record["verification"]["status"] != "PASS"):
            raise StateError("Latest recovery verification must PASS before recall")
        if stage == "diagnose" and record["state"] == State.FAILED:
            self.store.transition(record, State.DIAGNOSING)
        result = self.testing.evaluate(stage, answer)
        record["answers"].setdefault(stage, []).append({"answer": answer, "evaluation": result})
        if stage == "recall" and result["outcome"] == "pass":
            # MASTERED is local and narrow, requiring successful objective diagnosis + verified repair.
            diagnoses = record["answers"].get("diagnose", [])
            if diagnoses and diagnoses[-1]["evaluation"]["outcome"] == "pass" and not record["assistance"]["automated_demo"]:
                self.store.transition(record, State.MASTERED)
        self.save(record)
        return result

    def fix(self, run_id: str) -> dict:
        record = self.store.get(run_id)
        if record["state"] == State.DIAGNOSING:
            diagnosis = record["answers"].get("diagnose", [])
            if not diagnosis or diagnosis[-1]["evaluation"]["outcome"] != "pass":
                raise StateError("Submit a supported diagnosis before applying the repair")
            record["policy"] = "upsert"
            self.store.transition(record, State.REMEDIATED)
        elif record["state"] != State.REMEDIATED:
            raise StateError(f"Repair unavailable from {record['state']}")
        self.phase(record, "recovery", Warehouse(self.directory(record) / "warehouse.sqlite"), "upsert", record["fail_after_rows"])
        self.save(record)
        return record

    def verify(self, run_id: str) -> dict:
        record = self.store.get(run_id)
        if record["state"] not in {State.REMEDIATED, State.VERIFIED, State.MASTERED} or "recovery" not in record["phases"]:
            raise StateError("Repair and recovery must finish before verification")
        if record["state"] in {State.VERIFIED, State.MASTERED}:
            self.store.invalidate(record, "Rechecking current data; prior verification is suspended until new checks pass")
        record["verification"] = {"status": "RUNNING", "checks": {}}
        self.save(record)
        warehouse = Warehouse(self.directory(record) / "warehouse.sqlite")
        before = warehouse.rows()
        rerun = self.phase(record, "rerun", warehouse, record["policy"], record["fail_after_rows"])
        after = warehouse.rows()
        source = self.source(record)
        expected = sorted(source, key=lambda o: o["order_id"])
        recovery = record["phases"]["recovery"]
        fault_snapshot = self.observability.snapshot(str(self.directory(record) / "observability.sqlite"),
                                                    record["phases"]["fault"]["observability"]["snapshot_id"])
        checks = {
            "root_cause_resolved": record["policy"] == "upsert" and warehouse.has_key(),
            "data_corrected": after == expected and warehouse.rows("fct_orders") == expected,
            "quality_checks_pass": recovery["quality_status"] == rerun["quality_status"] == "PASS" and rerun["quality"]["gate_open"],
            "models_correct": recovery["model_status"] == rerun["model_status"] == "PASS",
            "downstream_recovered": not rerun["observability"]["incidents"] and rerun["dashboard"]["trusted"] and rerun["revenue"] == revenue(source),
            "rerun_safe": before == after and len(after) == 1000,
            "partial_write_retry_safe": len(rerun["attempts"]) == 2 and all(a["warehouse_rows_after_attempt"] == 1000 for a in rerun["attempts"]),
            "historic_failure_preserved": any(t.get("failures") == record["fail_after_rows"] for t in fault_snapshot["tests"]),
        }
        record["verification"] = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
        if not all(checks.values()) and record["state"] in {State.VERIFIED, State.MASTERED}:
            self.store.invalidate(record, "Latest verification failed; previous recovery or recall cannot certify current data")
        if all(checks.values()) and record["state"] == State.REMEDIATED:
            self.store.transition(record, State.VERIFIED)
            if not any(event["event_type"] == EventType.RUN_COMPLETED for event in record["events"]):
                emit(record, "lab", None, EventType.RUN_COMPLETED, "VERIFIED", record["verification"])
        self.save(record)
        return record

    def reset(self, scenario_id: str) -> dict:
        if scenario_id != SCENARIO_ID:
            raise ValueError("Unknown scenario")
        # New isolated exercise preserves prior attempts and evidence.
        return self.start()
