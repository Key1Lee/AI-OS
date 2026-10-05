from collections import Counter
from copy import deepcopy
import hashlib
import json

import pytest

from lab.contracts import Event, EventType, State
from lab.core import Lab, publication_decision
from lab.fixtures import commerce, key_batches, revenue
from lab.store import StateError, Store
from lab.telemetry import emit, openlineage
from lab.warehouse import Warehouse


def test_fixture_has_a_stable_independent_commerce_reference():
    first = commerce(42)
    assert first == commerce(42)
    assert len(first["orders"]) == 1000
    assert len({row["order_id"] for row in first["orders"]}) == 1000
    assert len(first["customers"]) == 20
    assert first["orders"][0]["order_amount"] == "10.79"
    assert first["orders"][-1]["order_amount"] == "20.42"
    assert revenue(first["orders"]) == "53945.00"
    assert revenue(commerce(7)["orders"]) == "53955.00"
    assert commerce(7) != first
    assert {row["order_id"] for row in first["order_items"]} == {row["order_id"] for row in first["orders"]}
    assert {row["order_id"] for row in first["payments"]} == {row["order_id"] for row in first["orders"]}
    first["orders"][0]["order_amount"] = "0.00"
    assert commerce(42)["orders"][0]["order_amount"] == "10.79"


def test_native_model_batches_cover_every_row_without_splitting_keys():
    source = commerce()["orders"][:201]
    rows = list(reversed(source + source[:2]))
    batches = key_batches(rows, limit=180)
    assert all(0 < len(batch) <= 180 for batch in batches)
    encode = lambda row: json.dumps(row, sort_keys=True)
    assert Counter(map(encode, rows)) == Counter(encode(row) for batch in batches for row in batch)
    owners = {}
    for index, batch in enumerate(batches):
        for row in batch:
            assert owners.setdefault(row["order_id"], index) == index
    assert [sorted(row["order_id"] for row in batch) for batch in batches] == [
        sorted(row["order_id"] for row in batch) for batch in key_batches(list(reversed(rows)), limit=180)]
    with pytest.raises(ValueError, match="key group exceeds"):
        key_batches([source[0]] * 181, limit=180)


def test_state_jump_is_rejected_without_mutating_saved_evidence(tmp_path):
    store = Store(tmp_path)
    record = {"run_id": "state-unit", "state": "READY", "transitions": []}
    store.save(record)
    original = deepcopy(record)
    with pytest.raises(StateError, match="Cannot move"):
        store.transition(record, State.VERIFIED)
    assert record == original
    assert store.get(record["run_id"]) == original
    store.transition(record, State.BASELINE)
    assert store.get(record["run_id"])["state"] == "BASELINE"
    assert record["transitions"] == [{"from": "READY", "to": "BASELINE"}]


def test_warehouse_repair_preserves_exact_cents_and_updates_changed_orders(tmp_path):
    warehouse = Warehouse(tmp_path / "warehouse.sqlite")
    source = commerce()["orders"][:2]
    source[0]["order_amount"], source[1]["order_amount"] = "0.29", "10.01"
    warehouse.write(source, "append")
    warehouse.write(source[:1], "append")
    assert len(warehouse.rows()) == 3
    with warehouse.connect() as db:
        assert [row[0] for row in db.execute("SELECT amount_cents FROM orders_raw ORDER BY rowid")] == [29, 1001, 29]
    warehouse.enable_upsert()
    assert warehouse.has_key()
    changed = {**source[0], "order_amount": "14.73"}
    warehouse.write([changed], "upsert")
    expected = [changed, source[1]]
    assert warehouse.rows() == expected
    warehouse.write(expected, "upsert")
    assert warehouse.rows() == expected
    warehouse.materialize(expected)
    assert warehouse.rows("fct_orders") == expected
    with warehouse.connect() as db:
        assert db.execute("SELECT amount_cents FROM orders_raw WHERE order_id=?", (changed["order_id"],)).fetchone()[0] == 1473


def test_event_correlation_and_parent_run_lineage_are_deterministic():
    record = {"run_id": "d41e56b2-c34a-4efa-8842-5b2d4c864bb1", "events": []}
    emit(record, "lab", None, EventType.RUN_STARTED, "RUNNING")
    emit(record, "orchestration", "orders_raw", EventType.ASSET_MATERIALIZED, "SUCCESS")
    emit(record, "lab", None, EventType.RUN_COMPLETED, "VERIFIED")
    assert len({event["event_id"] for event in record["events"]}) == 3
    assert all(event["run_id"] == record["run_id"] for event in record["events"])
    assert record["events"][0]["timestamp"] == "2026-10-03T00:00:01+00:00"
    assert record["events"][1]["upstream_assets"] == ("source.orders",)
    lineage = openlineage(record)
    assert [event["eventType"] for event in lineage] == ["START", "OTHER", "COMPLETE"]
    assert all(event["run"]["runId"] == record["run_id"] for event in lineage)
    assert lineage[1]["inputs"] == [{"namespace": "ae-lab/commerce", "name": "source.orders"}]
    assert lineage[1]["outputs"] == [{"namespace": "ae-lab/commerce", "name": "orders_raw"}]


@pytest.mark.parametrize("settings", [{"seed": "42"}, {"fail_after_rows": 0}, {"fail_after_rows": 1000}, {"fail_after_rows": True}])
def test_invalid_scenario_configuration_creates_no_run(tmp_path, settings):
    lab = Lab(tmp_path)
    with pytest.raises(ValueError):
        lab.start(**settings)
    assert lab.store.records() == []


def test_pinned_fixture_tampering_stops_execution_before_native_attempts(tmp_path):
    lab = Lab(tmp_path)
    record = lab.start()
    saved_before = lab.store.get(record["run_id"])
    fixture_path = lab.directory(record) / "fixtures.json"
    fixture_text = fixture_path.read_text()
    assert record["fixture_sha256"] == hashlib.sha256(fixture_text.encode()).hexdigest()
    changed = json.loads(fixture_text)
    changed["orders"][0]["order_amount"] = "99.99"
    fixture_path.write_text(json.dumps(changed, indent=2) + "\n")
    with pytest.raises(StateError, match="Pinned source fixture changed"):
        lab.source(record)
    with pytest.raises(StateError, match="Pinned source fixture changed"):
        lab.run(record["run_id"])
    saved = lab.store.get(record["run_id"])
    assert saved["state"] == State.READY
    assert saved["phases"] == {}
    assert saved["events"] == saved_before["events"]
    assert not (lab.directory(record) / "warehouse.sqlite").exists()
    assert Warehouse(lab.directory(record) / "baseline.sqlite").rows() == []


@pytest.mark.parametrize("overrides", [
    {"run_id": "not-a-uuid"}, {"timestamp": "2026-10-03T00:00:00"},
    {"status": "UNRECOGNIZED"}, {"metadata": ["invalid"]},
])
def test_canonical_event_rejects_invalid_correlation_or_evidence(overrides):
    fields = {"event_id": "unit-event:1", "timestamp": "2026-10-03T00:00:01+00:00",
              "run_id": "d41e56b2-c34a-4efa-8842-5b2d4c864bb1", "scenario_id": "ORCH-IDEMPOTENCY-001",
              "system": "lab", "asset": None, "event_type": EventType.RUN_STARTED,
              "status": "RUNNING", "metadata": {}}
    with pytest.raises(ValueError):
        Event(**(fields | overrides))


@pytest.mark.parametrize("section,field,value", [
    ("schedule", "status", "FAILED"), ("schedule", "status", None),
    ("model", "status", "FAIL"), ("model", "status", "UNKNOWN"),
    ("model", "row_count", None), ("model", "revenue", "NaN"),
    ("model", "revenue", "not money"), ("model", "revenue", "0.01"),
    ("quality", "status", "UNKNOWN"), ("quality", "gate_open", None),
    ("quality", "gate_open", 1), ("quality", "total_rows", None),
    ("quality", "validated_rows", 1), ("quality", "distinct_keys", None),
    ("quality", "duplicate_extra", 1),
])
def test_publication_requires_all_current_phase_evidence(section, field, value):
    source = commerce()["orders"][:2]
    evidence = {"schedule": {"status": "SUCCESS"},
                "model": {"status": "PASS", "row_count": 2, "revenue": revenue(source), "rows": source},
                "quality": {"status": "PASS", "gate_open": True, "total_rows": 2,
                            "validated_rows": 2, "distinct_keys": 2, "duplicate_extra": 0}}
    previous = publication_decision(**evidence, source=source, loaded=source, materialized=source)
    assert previous == {"trusted": True, "rejection_reasons": []}
    evidence[section][field] = value
    current = publication_decision(**evidence, source=source, loaded=source, materialized=source)
    assert current["trusted"] is False and current["rejection_reasons"]
    assert previous["trusted"] is True  # Prior evidence cannot stand in for current checks.


@pytest.mark.parametrize("missing", ["schedule", "model", "quality"])
def test_missing_native_receipt_blocks_publication(missing):
    source = commerce()["orders"][:2]
    evidence = {"schedule": {"status": "SUCCESS"},
                "model": {"status": "PASS", "row_count": 2, "revenue": revenue(source), "rows": source},
                "quality": {"status": "PASS", "gate_open": True, "total_rows": 2,
                            "validated_rows": 2, "distinct_keys": 2, "duplicate_extra": 0}}
    evidence[missing] = None
    assert publication_decision(**evidence, source=source, loaded=source, materialized=source)["trusted"] is False


def test_publication_binds_persisted_rows_to_native_certified_output():
    source = commerce()["orders"][:2]
    model = {"status": "PASS", "row_count": 2, "revenue": revenue(source), "rows": source}
    quality = {"status": "PASS", "gate_open": True, "total_rows": 2,
               "validated_rows": 2, "distinct_keys": 2, "duplicate_extra": 0}
    decide = lambda rows: publication_decision({"status": "SUCCESS"}, model, quality, source, source, rows)
    assert decide(list(reversed(source)))["trusted"] is True
    changed = deepcopy(source)
    changed[0]["customer_id"], changed[1]["customer_id"] = changed[1]["customer_id"], changed[0]["customer_id"]
    assert revenue(changed) == revenue(source)
    assert decide(changed)["rejection_reasons"] == ["materialized_output_matches_model"]
    model.pop("rows")
    assert decide(source)["trusted"] is False
