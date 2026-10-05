"""Read-only product probes authored by the independent Phase 1 verifier.

All writes target a temporary Lab profile; native adapters run unchanged siblings.
Run from the Lab root: uv run python docs/verification-probes/independent_phase1.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.adapters.bridge import AdapterError, PROJECTS, project_path
from lab.adapters.modeling import NativeModelingAdapter
from lab.adapters.quality import NativeQualityAdapter
from lab.core import Lab
from lab.fixtures import commerce, key_batches, revenue
from lab.store import StateError
from lab.warehouse import Warehouse


def fingerprint_siblings():
    excluded = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", "dist", "build", ".next"}
    suffixes = {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".toml", ".yaml", ".yml", ".md", ".sql", ".txt", ".lock"}
    result = {}
    for system in PROJECTS:
        root = project_path(system)
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if path.is_file() and not any(part in excluded for part in relative.parts) and path.suffix in suffixes:
                result[f"{system}/{relative}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    before = fingerprint_siblings()
    source = commerce()["orders"]
    assert commerce() == commerce(42)
    assert commerce(41) != commerce(42)
    assert revenue(source) == "53945.00"
    assert revenue(source[:700] + source) == "91448.50"
    checks = {"fixture_deterministic_exact_money": True}

    shuffled = list(reversed(source)) + [deepcopy(source[179]), deepcopy(source[359]), deepcopy(source[0])]
    batches = key_batches(shuffled)
    assert sum(map(len, batches)) == 1003
    assert max(map(len, batches)) <= 180
    owners = {}
    for index, batch in enumerate(batches):
        for order in batch:
            assert owners.setdefault(order["order_id"], index) == index
    checks["bounded_batches_keep_nonadjacent_duplicate_keys_together"] = True
    model = NativeModelingAdapter().build(shuffled, source, "independent-model-boundary")
    assert model["status"] == "FAIL" and model["row_count"] == 1003
    assert revenue(model["rows"]) == revenue(shuffled)
    quality = NativeQualityAdapter().validate(shuffled, "independent-quality-boundary", "2026-10-03T00:00:00+00:00")
    assert quality["status"] == "FAIL" and quality["duplicate_extra"] == 3
    assert quality["validated_rows"] == 1003
    checks["native_adapters_detect_distributed_duplicates_without_hiding_rows"] = True
    try:
        NativeModelingAdapter().build([source[0]] * 181, source, "independent-oversize")
    except AdapterError:
        checks["native_modeling_oversize_key_group_fails_closed"] = True
    else:
        raise AssertionError("Oversized duplicate group escaped native modeling limit")

    with tempfile.TemporaryDirectory(prefix="ae-lab-independent-") as temp:
        lab = Lab(Path(temp))
        record = lab.run()
        run_id = record["run_id"]
        fault = record["phases"]["fault"]
        assert record["state"] == "FAILED"
        assert fault["rows"] == 1700 and fault["duplicate_extra"] == 700 and fault["revenue"] == "91448.50"
        assert fault["pipeline_status"] == "SUCCESS" and fault["quality_status"] == fault["model_status"] == "FAIL"
        assert fault["publication"] == "BLOCKED" and not fault["dashboard"]["trusted"]
        assert len(fault["attempts"]) == 2
        assert [attempt["warehouse_rows_after_attempt"] for attempt in fault["attempts"]] == [700, 1700]
        fault_id = fault["observability"]["snapshot_id"]
        checks["real_native_failure_and_publication_impact"] = True
        try:
            lab.fix(run_id)
        except StateError:
            checks["repair_requires_recorded_diagnosis"] = True
        else:
            raise AssertionError("Repair bypassed diagnosis")
        denied = lab.answer(run_id, "diagnose", {"reason": "ingestion idempotency duplicate_order_ids"})
        assert denied["outcome"] == "fail"
        try:
            lab.fix(run_id)
        except StateError:
            checks["prose_keywords_do_not_grant_repair"] = True
        else:
            raise AssertionError("Prose keywords bypassed native objective enforcement")
        passed = lab.answer(run_id, "diagnose", {"layer": "ingestion", "property": "idempotency", "signal": "duplicate_order_ids"})
        assert passed["outcome"] == "pass"
        record = Lab(Path(temp)).fix(run_id)
        assert record["state"] == "REMEDIATED"
        record = Lab(Path(temp)).verify(run_id)
        assert record["state"] == "VERIFIED" and record["verification"]["status"] == "PASS"
        assert all(record["verification"]["checks"].values())
        assert record["phases"]["rerun"]["rows"] == 1000
        assert record["phases"]["rerun"]["revenue"] == "53945.00"
        historic = lab.observability.snapshot(str(lab.directory(record) / "observability.sqlite"), fault_id)
        assert any(test["failures"] == 700 for test in historic["tests"])
        assert record["phases"]["rerun"]["observability"]["incidents"] == []
        checks["resumed_real_recovery_complete_data_retry_safety_and_historic_incident"] = True
        record = Lab(Path(temp)).verify(run_id)
        assert record["verification"]["status"] == "PASS"
        checks["verification_can_repeat_without_reintroducing_corruption"] = True
        with Warehouse(lab.directory(record) / "warehouse.sqlite").connect() as db:
            # Compensating amount corruption leaves the row count and aggregate unchanged.
            db.execute("UPDATE orders_raw SET amount_cents=amount_cents+1 WHERE order_id='O0001'")
            db.execute("UPDATE orders_raw SET amount_cents=amount_cents-1 WHERE order_id='O0002'")
        record = Lab(Path(temp)).verify(run_id)
        assert record["verification"]["status"] == "FAIL"
        assert not record["verification"]["checks"]["rerun_safe"]
        checks["compensating_row_corruption_cannot_pass_repeat_safety"] = True
        try:
            lab.answer(run_id, "recall", {"rows": 1000, "key": "order_id", "repair": "upsert"})
        except StateError:
            checks["latest_failed_verification_cannot_award_mastery"] = True
        else:
            raise AssertionError("Recall awarded after latest verification failed")
        record = Lab(Path(temp)).verify(run_id)
        assert record["verification"]["status"] == "PASS"
        assert sum(event["event_type"] == "RUN_COMPLETED" for event in record["events"]) == 1
        checks["repeat_verification_preserves_one_parent_completion_event"] = True
        record["assistance"]["automated_demo"] = True
        lab.save(record)
        outcome = lab.answer(run_id, "recall", {"rows": 1000, "key": "order_id", "repair": "upsert"})
        assert outcome["outcome"] == "pass" and lab.store.get(run_id)["state"] == "VERIFIED"
        checks["automated_assistance_cannot_award_local_mastery"] = True
        record = lab.store.get(run_id)
        old_id = record["run_id"]
        new = lab.reset(record["scenario_id"])
        assert new["run_id"] != old_id and lab.store.get(old_id)["state"] == "VERIFIED"
        checks["reset_preserves_prior_evidence"] = True
        fixture_file = lab.directory(new) / "fixtures.json"
        fixture_file.write_text(fixture_file.read_text() + " ")
        try:
            lab.source(new)
        except StateError:
            checks["modified_pinned_fixture_cannot_substitute_a_new_source"] = True
        else:
            raise AssertionError("Modified fixture bypassed the deterministic source pin")
        exported = json.loads((lab.directory(record) / "evidence.json").read_text())
        assert exported["verification"] == record["verification"]
        events = exported["events"]
        assert len({event["event_id"] for event in events}) == len(events)
        assert all(event["run_id"] == old_id and event["scenario_id"] == "ORCH-IDEMPOTENCY-001" for event in events)
        assert all(a["timestamp"] < b["timestamp"] for a, b in zip(events, events[1:]))
        checks["exported_canonical_events_correlate_and_order"] = True
        baseline_events = [event for event in events if event["metadata"].get("phase") == "baseline"]
        assert not any(event["event_type"] in {"INCIDENT_OPENED", "INCIDENT_RESOLVED"} for event in baseline_events)
        opened = {event["metadata"]["incident_key"]: event for event in events if event["event_type"] == "INCIDENT_OPENED"}
        resolutions = [event for event in events if event["event_type"] == "INCIDENT_RESOLVED"]
        assert opened and resolutions
        for event in resolutions:
            prior = opened[event["metadata"]["incident_key"]]
            assert event["metadata"]["opened_event_id"] == prior["event_id"]
            assert event["timestamp"] > prior["timestamp"]
        checks["incident_events_resolve_real_correlated_prior_failures"] = True
    after = fingerprint_siblings()
    assert before == after, sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
    checks["sibling_source_and_config_digests_unchanged_during_probes"] = True
    print(json.dumps({"status": "PASS", "checks": checks, "native_source_and_config_files_compared": len(before)}, indent=2))


if __name__ == "__main__":
    main()
