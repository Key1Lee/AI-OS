from __future__ import annotations

import pytest

from lab.adapters.bridge import AdapterError
from lab.adapters.observability import NativeObservabilityAdapter


def evidence(phase="fault", **overrides):
    values = {"run_id": "contract-run-001", "scenario_id": "ORCH-IDEMPOTENCY-001",
              "timestamp": "2026-10-03T12:00:00+00:00", "phase": phase,
              "rows": 1700, "expected_rows": 1000, "duplicate_extra": 700,
              "revenue": 17000, "expected_revenue": 10000,
              "quality_status": "FAIL", "model_status": "FAIL", "measurement_unit": "USD cents"}
    return {**values, **overrides}


def test_native_incident_quality_evidence_and_declared_dashboard_impact(tmp_path):
    adapter = NativeObservabilityAdapter()
    result = adapter.observe(evidence(), str(tmp_path / "observability.db"))
    assert result["incidents"][0]["node_id"] == "model.ae_lab.fct_orders"
    assert result["impact"] == ["executive_dashboard"]
    assert result["native_refs"]["contract_version"] == "data-map-v1"
    assert result["native_refs"]["database"] == str(tmp_path / "observability.db")
    assert result["tests"][0]["status"] == "FAILED"
    assert result["tests"][0]["failures"] == 700
    model_execution = next(item for item in result["executions"] if item["node_id"] == "model.ae_lab.fct_orders")
    assert model_execution["status"] == "FAILED"
    assert {column["name"]: column["data_type"] for column in result["schemas"]["fct_orders"]} == {
        "order_id": "VARCHAR", "customer_id": "VARCHAR", "status": "VARCHAR",
        "order_amount": "DECIMAL(18,2)", "currency": "VARCHAR", "ordered_at": "TIMESTAMP WITH TIME ZONE"}
    measured_revenue = next(item for item in result["observations"] if item["evidence_type"] == "reconciled_revenue_usd_cents")
    assert measured_revenue["actual"] == 17000
    assert measured_revenue["measurement_unit"] == "USD cents"
    assert result["provenance"]["measurement_unit"] == "USD cents"
    assert "measurement_unit=USD cents" in result["native_refs"]["artifacts"]["manifest.json"]["producer"]
    assert len(result["lineage"]) == 6
    assert "no dbt command executed" in result["provenance"]["producer"]


def test_recovery_clears_current_incident_and_preserves_pinned_failure(tmp_path):
    database = str(tmp_path / "observability.db")
    adapter = NativeObservabilityAdapter()
    fault = adapter.observe(evidence(), database)
    recovered = adapter.observe(evidence("recovery", rows=1000, duplicate_extra=0,
                                         revenue=10000, quality_status="PASS", model_status="PASS"), database)
    assert recovered["incidents"] == []
    assert recovered["impact"] == []
    assert recovered["snapshot_id"] != fault["snapshot_id"]
    assert adapter.snapshot(database, fault["snapshot_id"])["tests"][0]["failures"] == 700
    assert adapter.snapshot(database, recovered["snapshot_id"])["tests"][0]["status"] == "HEALTHY"


def test_same_measured_evidence_has_stable_snapshot_identity(tmp_path):
    adapter = NativeObservabilityAdapter()
    database = str(tmp_path / "observability.db")
    first = adapter.observe(evidence(), database)
    again = adapter.observe(evidence(), database)
    assert first["snapshot_id"] == again["snapshot_id"]


def test_contradictory_quality_evidence_is_rejected(tmp_path):
    adapter = NativeObservabilityAdapter()
    with pytest.raises(AdapterError, match="contradicts"):
        adapter.observe(evidence(quality_status="PASS"), str(tmp_path / "observability.db"))


def test_missing_database_is_rejected():
    with pytest.raises(ValueError, match="isolated"):
        NativeObservabilityAdapter().observe(evidence(), "")


def test_revenue_must_use_exact_integer_cents(tmp_path):
    with pytest.raises(AdapterError, match="integer measurement in USD cents"):
        NativeObservabilityAdapter().observe(evidence(revenue=170.0), str(tmp_path / "observability.db"))
