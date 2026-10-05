from copy import deepcopy
import json

import pytest

from lab.contracts import State
from lab.core import Lab
from lab.fixtures import commerce, revenue
from lab.store import StateError
from lab.warehouse import Warehouse


def test_real_pipeline_configured_failure_diagnosis_repair_and_repeated_retry(tmp_path):
    lab = Lab(tmp_path / "profile-a")
    record = lab.run(seed=7, fail_after_rows=37)
    run_id = record["run_id"]
    directory = lab.directory(record)
    source = commerce(7)["orders"]
    assert record["seed"] == 7 and record["fail_after_rows"] == 37
    assert record["state"] == State.FAILED
    assert lab.source(record) == source
    assert record["phases"]["baseline"]["quality_status"] == "PASS"
    fault = record["phases"]["fault"]
    assert (fault["rows"], fault["duplicate_extra"], fault["pipeline_status"],
            fault["quality_status"], fault["model_status"]) == (1037, 37, "SUCCESS", "FAIL", "FAIL")
    assert [attempt["warehouse_rows_after_attempt"] for attempt in fault["attempts"]] == [37, 1037]
    assert fault["revenue"] == revenue(source[:37] + source)
    assert fault["publication"] == "BLOCKED"
    assert fault["dashboard"]["trusted"] is False
    assert fault["observability"]["impact"] == ["executive_dashboard"]
    assert fault["freshness"] == "NOT_MEASURED"
    fault_before = deepcopy(fault)
    database = str(directory / "observability.sqlite")
    pinned_id = fault["observability"]["snapshot_id"]
    snapshot_before = lab.observability.snapshot(database, pinned_id)

    wrong = lab.answer(run_id, "diagnose", {"layer": "quality", "property": "freshness",
                                           "signal": "duplicate_order_ids", "reason": "Wrong layer"})
    assert wrong["outcome"] == "fail"
    with pytest.raises(StateError, match="supported diagnosis"):
        lab.fix(run_id)
    assert lab.store.get(run_id)["state"] == State.DIAGNOSING
    assert lab.store.get(run_id)["policy"] == "append"
    correct = lab.answer(run_id, "diagnose", {"layer": "ingestion", "property": "idempotency",
                                             "signal": "duplicate_order_ids", "reason": "The retry repeats 37 committed order keys."})
    assert correct["outcome"] == "pass"
    repaired = lab.fix(run_id)
    assert repaired["state"] == State.REMEDIATED
    assert repaired["policy"] == "upsert"
    assert repaired["phases"]["recovery"]["rows"] == 1000
    assert repaired["phases"]["recovery"]["observability"]["incidents"] == []
    warehouse = Warehouse(directory / "warehouse.sqlite")
    expected = sorted(source, key=lambda row: row["order_id"])
    assert warehouse.rows() == expected
    assert warehouse.rows("fct_orders") == expected
    before_rerun = deepcopy(warehouse.rows())
    verified = lab.verify(run_id)
    assert verified["state"] == State.VERIFIED
    assert verified["verification"]["status"] == "PASS"
    assert all(verified["verification"]["checks"].values())
    assert warehouse.rows() == before_rerun == expected
    assert warehouse.rows("fct_orders") == expected
    assert warehouse.has_key()
    rerun = verified["phases"]["rerun"]
    assert [attempt["native"]["status"] for attempt in rerun["attempts"]] == ["FAILED", "SUCCESS"]
    assert [attempt["warehouse_rows_after_attempt"] for attempt in rerun["attempts"]] == [1000, 1000]
    assert (rerun["quality_status"], rerun["model_status"], rerun["duplicate_extra"],
            rerun["revenue"], rerun["publication"]) == ("PASS", "PASS", 0, "53955.00", "ELIGIBLE")
    assert rerun["dashboard"]["trusted"] is True
    assert verified["phases"]["fault"] == fault_before
    assert lab.observability.snapshot(database, pinned_id) == snapshot_before
    assert any(test["failures"] == 37 for test in snapshot_before["tests"])
    assert json.loads((directory / "evidence.json").read_text())["verification"] == verified["verification"]
    assert len((directory / "events.jsonl").read_text().splitlines()) == len(verified["events"])
    assert all(event["run_id"] == run_id for event in verified["events"])

    # Equal and opposite errors evade aggregate revenue comparisons. The latest
    # verification must still invalidate the previous result when rows changed.
    with warehouse.connect() as db:
        db.execute("UPDATE orders_raw SET amount_cents=amount_cents+1 WHERE order_id=?", (source[0]["order_id"],))
        db.execute("UPDATE orders_raw SET amount_cents=amount_cents-1 WHERE order_id=?", (source[1]["order_id"],))
    assert revenue(warehouse.rows()) == revenue(source)
    assert warehouse.rows() != expected
    invalidated = lab.verify(run_id)
    assert invalidated["verification"]["status"] == "FAIL"
    assert invalidated["verification"]["checks"]["rerun_safe"] is False
    assert invalidated["verification"]["checks"]["data_corrected"] is True
    assert invalidated["state"] == State.REMEDIATED
    assert invalidated["transitions"][-1]["from"] == State.VERIFIED
    assert invalidated["transitions"][-1]["to"] == State.REMEDIATED
    recall = {"rows": 1000, "key": "order_id", "repair": "upsert"}
    with pytest.raises(StateError, match="recall unavailable"):
        lab.answer(run_id, "recall", recall)
    reverified = lab.verify(run_id)
    assert reverified["verification"]["status"] == "PASS"
    assert reverified["state"] == State.VERIFIED
    assert all(reverified["verification"]["checks"].values())
    assert warehouse.rows() == expected
    assert lab.observability.snapshot(database, pinned_id) == snapshot_before
    reverified["assistance"]["automated_demo"] = True
    lab.save(reverified)
    evaluated = lab.answer(run_id, "recall", recall)
    assert evaluated["outcome"] == "pass"
    assert lab.store.get(run_id)["state"] == State.VERIFIED
    assert lab.store.get(run_id)["assistance"]["automated_demo"] is True

    other = Lab(tmp_path / "profile-b")
    assert other.store.records() == []
    ready = other.start(seed=42, fail_after_rows=700)
    assert ready["run_id"] != run_id and ready["state"] == State.READY
    assert revenue(other.source(ready)) == "53945.00"
    assert lab.store.get(run_id)["state"] == State.VERIFIED
    assert len(lab.store.records()) == len(other.store.records()) == 1


@pytest.mark.parametrize("offsetting", [False, True])
def test_native_publication_blocks_wrong_rows_before_recovery_verification(tmp_path, offsetting):
    class CorruptAmount(Warehouse):
        def write(self, orders, policy):
            super().write(orders, policy)
            with self.connect() as db:
                db.execute("UPDATE orders_raw SET amount_cents=amount_cents+100 WHERE order_id='O0001'")
                if offsetting:
                    db.execute("UPDATE orders_raw SET amount_cents=amount_cents-100 WHERE order_id='O0002'")

    lab = Lab(tmp_path / "publication")
    record = lab.start()
    path = lab.directory(record) / "warehouse.sqlite"
    clean = lab.phase(record, "baseline", Warehouse(path), "upsert", None)
    assert clean["publication"] == "ELIGIBLE" and clean["dashboard"]["trusted"] is True
    corrupt = lab.phase(record, "baseline", CorruptAmount(path), "upsert", None)
    assert corrupt["quality_status"] == "PASS" and corrupt["quality"]["gate_open"] is True
    assert corrupt["rows"] == corrupt["expected_rows"] == 1000 and corrupt["duplicate_extra"] == 0
    assert corrupt["model_status"] == "FAIL"
    assert (corrupt["revenue"] == corrupt["expected_revenue"]) is offsetting
    assert corrupt["publication"] == "BLOCKED" and corrupt["dashboard"]["trusted"] is False
    assert "model_correctness" in corrupt["publication_rejections"]
    assert lab.store.get(record["run_id"])["phases"]["baseline"]["dashboard"]["trusted"] is False
    assert lab.source(record) == commerce()["orders"]
    recovered = lab.phase(record, "recovery", Warehouse(path), "upsert", None)
    assert recovered["publication"] == "ELIGIBLE" and recovered["dashboard"]["trusted"] is True
    assert recovered["publication_rejections"] == []


def test_native_publication_rejects_changed_materialization_with_equal_total(tmp_path):
    class ChangedMaterialization(Warehouse):
        def materialize(self, orders):
            super().materialize(orders)
            with self.connect() as db:
                db.execute("UPDATE fct_orders SET amount_cents=amount_cents+17 WHERE order_id='O0001'")
                db.execute("UPDATE fct_orders SET amount_cents=amount_cents-17 WHERE order_id='O0002'")

    lab = Lab(tmp_path / "binding")
    record = lab.start()
    warehouse = ChangedMaterialization(lab.directory(record) / "warehouse.sqlite")
    result = lab.phase(record, "baseline", warehouse, "upsert", None)
    assert result["model_status"] == result["quality_status"] == "PASS"
    assert revenue(warehouse.rows("fct_orders")) == result["expected_revenue"]
    assert warehouse.rows("fct_orders") != result["modeling"]["rows"]
    assert result["publication"] == "BLOCKED" and result["dashboard"]["trusted"] is False
    assert result["publication_rejections"] == ["materialized_output_matches_model"]
