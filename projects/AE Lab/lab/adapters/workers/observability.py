"""Runs in the Observability project's Python runtime; owns no engine logic."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from data_system_map import create_service

SYSTEM_ID = "ae-lab-idempotency"
PRODUCER = "AE Lab adapter-generated metadata from measured Lab evidence; no dbt command executed"
SOURCE = "source.ae_lab.orders"
ASSETS = ["orders_raw", "stg_orders", "int_orders_enriched", "fct_orders", "revenue"]
NODES = {name: f"model.ae_lab.{name}" for name in ASSETS}
DASHBOARD = "exposure.ae_lab.executive_dashboard"
TEST = "test.ae_lab.unique_order_id"
MEASUREMENT_UNIT = "USD cents"


def validate(evidence):
    if not isinstance(evidence, dict):
        raise ValueError("Observability evidence must be an object.")
    for key in ("run_id", "scenario_id", "timestamp"):
        if not isinstance(evidence.get(key), str) or not evidence[key]:
            raise ValueError(f"Observability evidence requires {key}.")
    if evidence.get("phase") not in {"baseline", "fault", "recovery", "rerun"}:
        raise ValueError("Unsupported observability phase.")
    for key in ("rows", "expected_rows", "duplicate_extra"):
        if type(evidence.get(key)) is not int or evidence[key] < 0:
            raise ValueError(f"{key} must be a nonnegative count.")
    for key in ("revenue", "expected_revenue"):
        if type(evidence.get(key)) is not int:
            raise ValueError(f"{key} must be an integer measurement in USD cents.")
    if evidence.get("measurement_unit", MEASUREMENT_UNIT) != MEASUREMENT_UNIT:
        raise ValueError("Revenue measurements must use USD cents.")
    for key in ("quality_status", "model_status"):
        if evidence.get(key) not in {"PASS", "FAIL"}:
            raise ValueError(f"{key} must be PASS or FAIL.")
    if evidence["quality_status"] == "PASS" and evidence["duplicate_extra"]:
        raise ValueError("Passing uniqueness evidence contradicts duplicate measurements.")
    return evidence


def artifacts(evidence):
    stamp, run_id = evidence["timestamp"], evidence["run_id"]
    observation_id = f"run-{run_id}"
    metadata = {"generated_at": stamp, "invocation_id": run_id,
                "producer": f"{PRODUCER}; scenario={evidence['scenario_id']}; phase={evidence['phase']}; measurement_unit={MEASUREMENT_UNIT}",
                "sample": True}

    def observations(rows, duplicates):
        return [
            {"evidence_type": "row_count", "expected": evidence["expected_rows"],
             "actual": rows, "comparison_key": "order_id", "observation_id": observation_id},
            {"evidence_type": "duplicate_extra_rows", "expected": 0, "actual": duplicates,
             "comparison_key": "order_id", "observation_id": observation_id},
        ]

    order_types = {"order_id": "VARCHAR", "customer_id": "VARCHAR", "status": "VARCHAR",
                   "order_amount": "DECIMAL(18,2)", "currency": "VARCHAR",
                   "ordered_at": "TIMESTAMP WITH TIME ZONE"}
    columns = {name: {"name": name, "data_type": dtype} for name, dtype in order_types.items()}
    revenue_columns = {"revenue_cents": {"name": "revenue_cents", "data_type": "BIGINT",
                                         "description": "Gross completed-order revenue measured exactly in USD cents."}}
    source = {"unique_id": SOURCE, "name": "source.orders", "resource_type": "source",
              "schema": "fixture", "source_name": "deterministic_commerce_fixture",
              "description": "Seeded source orders; source measurements precede the injected loader fault.",
              "columns": columns, "depends_on": {"nodes": []},
              "meta": {"layer": "source", "grain": "One row per order", "primary_keys": ["order_id"],
                       "data_system_map": {"observations": observations(evidence["expected_rows"], 0)}}}
    nodes = {}
    parent = SOURCE
    for name in ASSETS:
        key = NODES[name]
        meta = {"layer": "staging" if name == "stg_orders" else "mart" if name in {"fct_orders", "revenue"} else "transformation",
                "grain": "One revenue total" if name == "revenue" else "One row per order (declared contract)",
                "primary_keys": [] if name == "revenue" else ["order_id"], "owner": "AE Lab"}
        if name in {"orders_raw", "fct_orders"}:
            meta["data_system_map"] = {"observations": observations(evidence["rows"], evidence["duplicate_extra"])}
        if name == "revenue":
            meta["data_system_map"] = {"observations": [{
                "evidence_type": "reconciled_revenue_usd_cents", "expected": evidence["expected_revenue"],
                "actual": evidence["revenue"], "comparison_key": "all_fixture_orders",
                "observation_id": observation_id, "measurement_unit": MEASUREMENT_UNIT}]}
        nodes[key] = {"unique_id": key, "resource_type": "model", "name": name,
                      "schema": "lab", "depends_on": {"nodes": [parent]}, "columns": columns if name != "revenue" else revenue_columns,
                      "meta": meta, "description": "Declared Lab pipeline asset. Execution is recorded only when measured by the native modeling run."}
        sql = evidence.get("model_sql")
        if isinstance(sql, dict) and isinstance(sql.get(name), str):
            nodes[key]["raw_code"] = sql[name]
        elif name == "fct_orders" and isinstance(sql, str):
            nodes[key]["raw_code"] = sql
        parent = key
    nodes[TEST] = {"unique_id": TEST, "resource_type": "test", "name": "Unique order IDs",
                   "attached_node": NODES["fct_orders"], "depends_on": {"nodes": [NODES["fct_orders"]]},
                   "test_metadata": {"name": "unique", "kwargs": {"column_name": "order_id"}},
                   "config": {"severity": "ERROR"}, "meta": {"layer": "mart"}, "columns": {}}
    manifest = {"metadata": {**metadata, "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json"},
                "sources": {SOURCE: source}, "nodes": nodes,
                "exposures": {DASHBOARD: {"unique_id": DASHBOARD, "resource_type": "exposure", "name": "executive_dashboard",
                    "description": "Declared consumer of the measured revenue output.", "depends_on": {"nodes": [NODES["revenue"]]},
                    "meta": {"layer": "output", "owner": "Commerce stakeholder"}, "columns": {}}}}
    results = [{"unique_id": NODES["fct_orders"], "status": "success" if evidence["model_status"] == "PASS" else "error",
                "message": f"Native modeling outcome translated by Lab during {evidence['phase']}; not a dbt execution.",
                "timing": [{"name": "execute", "started_at": stamp, "completed_at": stamp}]},
               {"unique_id": TEST, "status": "pass" if evidence["quality_status"] == "PASS" else "fail",
                "failures": evidence["duplicate_extra"],
                "message": "Native Data Quality result translated by Lab; duplicate extra rows are the recorded failure measure."}]
    run_results = {"metadata": {**metadata, "dbt_schema_version": "https://schemas.getdbt.com/dbt/run-results/v6.json"},
                   "args": {"which": "run"}, "results": results}
    return manifest, run_results


def summarize(engine, snapshot, database):
    pinned = {"snapshot_id": snapshot.snapshot_id}
    incidents = engine.incidents(SYSTEM_ID, **pinned)
    impacted = []
    for incident in incidents:
        for node in engine.impact(SYSTEM_ID, incident["node_id"], **pinned).get("affected_outputs", []):
            if node["name"] not in impacted:
                impacted.append(node["name"])
    return {"snapshot_id": snapshot.snapshot_id, "incidents": incidents, "impact": impacted,
            "lineage": [{"from": edge.from_node, "to": edge.to_node} for edge in snapshot.edges if edge.relationship_type == "depends_on"],
            "observations": [{**item.model_dump(), **({"measurement_unit": MEASUREMENT_UNIT}
                             if item.evidence_type == "reconciled_revenue_usd_cents" else {})}
                             for item in snapshot.observations],
            "tests": [item.model_dump() for item in snapshot.tests],
            "executions": [item.model_dump() for item in snapshot.executions],
            "schemas": {node.name: [column.model_dump() for column in node.columns]
                        for node in snapshot.nodes if node.node_type != "test"},
            "native_refs": {"system_id": SYSTEM_ID, "snapshot_id": snapshot.snapshot_id,
                            "database": str(database), "contract_version": snapshot.contract_version,
                            "assets": {"source.orders": SOURCE, **NODES, "executive_dashboard": DASHBOARD},
                            "artifacts": snapshot.artifacts},
            "provenance": {"classification": "FACT", "producer": PRODUCER,
                           "lineage_basis": "Declared adapter asset dependencies; not observed row movement.",
                           "measurements_basis": "Native execution and quality evidence supplied by the Lab coordinator.",
                           "measurement_unit": MEASUREMENT_UNIT,
                           "root_cause": "Unknown in the observability engine; learner diagnosis is evaluated separately."}}


def main():
    request = json.load(sys.stdin)
    database = Path(request["database"])
    if not database.is_absolute():
        raise ValueError("An absolute isolated database path is required.")
    operation = request.get("operation")
    evidence = validate(request["evidence"]) if operation == "observe" else None
    engine = create_service(database, seed_demo=False)
    if request.get("operation") == "snapshot":
        snapshot = engine.snapshot(SYSTEM_ID, request["snapshot_id"])
    elif request.get("operation") == "observe":
        manifest, run_results = artifacts(evidence)
        snapshot = engine.import_dbt(SYSTEM_ID, "AE Lab: retry safety", manifest, run_results=run_results)
    else:
        raise ValueError("Unsupported observability bridge operation.")
    print(json.dumps(summarize(engine, snapshot, database), allow_nan=False))


if __name__ == "__main__":
    main()
