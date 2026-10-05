from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

import yaml

from .contracts import Column, DataContract, Evidence, QualityEvent, QualityRule, ValidationResult, aware
from .engine import bounded_id, compile_contract


def observability_test(event: QualityEvent, name: str) -> dict:
    """Consumer-ready existing data-map-v1 TestResult shape, not an ingestion service."""
    return {"node_id": event.dataset_id, "test_id": event.rule_id, "test_name": name,
            "status": {"PASS": "HEALTHY", "WARN": "WARNING", "FAIL": "FAILED", "UNKNOWN": "UNKNOWN"}[event.status],
            "reported_status": event.status, "severity": event.severity, "failures": event.failure_count,
            "column": None, "association": "confirmed", "evidence": event.evidence.message,
            "provenance": {"source": "quality-event-v1", "pointer": f"/{event.run_id}/{event.rule_id}",
                           "classification": "FACT", "timestamp": event.timestamp,
                           "note": f"Input fingerprint {event.input_fingerprint}; consumer resolves its own dataset node ID."}}


def _modeling_column(value: dict[str, Any]) -> Column:
    raw = str(value.get("data_type", "")).upper().strip()
    mapping = {"VARCHAR": "STRING", "TEXT": "STRING", "STRING": "STRING", "INTEGER": "INTEGER", "BIGINT": "INTEGER",
               "BOOLEAN": "BOOLEAN", "TIMESTAMP WITH TIME ZONE": "TIMESTAMP", "TIMESTAMPTZ": "TIMESTAMP"}
    match = re.fullmatch(r"DECIMAL\((\d+),\s*(\d+)\)", raw)
    if match:
        dtype, precision, scale = "DECIMAL", int(match[1]), int(match[2])
    elif raw in mapping:
        dtype, precision, scale = mapping[raw], 18, 2
    else:
        raise ValueError(f"Unsupported Modeling type {raw}; do not guess timezone or precision")
    return Column(name=value["name"], data_type=dtype, nullable=value["nullable"],
                  description=value.get("description", ""), precision=precision, scale=scale)


def contract_from_modeling(envelope: dict) -> DataContract:
    """Map the explicit desired fact_contract. Observed ModelDefinition columns are not promises."""
    if envelope.get("contract_version") != "modeling-lab-v1":
        raise ValueError("Expected modeling-lab-v1")
    designed = envelope.get("fact_contract")
    dataset_id = envelope.get("dataset_id", "fct_orders")
    if not isinstance(designed, dict) or not designed.get("grain") or not designed.get("semantic_meaning"):
        raise ValueError("Explicit Modeling fact_contract is required; observed columns do not define desired state")
    return DataContract(id=bounded_id(f"{dataset_id}_modeling"), dataset_id=dataset_id,
        grain=f"1 row / {designed['grain']}", primary_key=designed["primary_key"],
        columns=[_modeling_column(c) for c in designed["columns"]], owner=designed.get("owner", "Analytics engineering"),
        semantic_meaning=designed["semantic_meaning"])


def dbt_export(contract: DataContract) -> dict:
    """Export supported provider checks and explicit unsupported IDs. No warehouse execution."""
    rules = compile_contract(contract)
    model_tests, column_tests, unsupported = [], {c.name: [] for c in contract.columns}, []
    for rule in rules:
        exp = rule.expectation
        config = {"severity": "error" if rule.severity == "CRITICAL" else "warn",
                  "meta": {"quality_rule_id": rule.id, "blocking": rule.blocking, "dimension": rule.dimension}}
        test, column, arguments = None, None, {}
        if exp.kind == "unique":
            test, arguments = "quality_unique_key", {"columns": exp.columns, "null_policy": exp.null_policy}
        elif exp.kind == "not_null" and exp.minimum_rate == 1:
            test, column = "not_null", exp.column
        elif exp.kind == "not_null" and exp.minimum_rate.as_tuple().exponent >= -18:
            test, column, arguments = "quality_completeness", exp.column, {"minimum_rate": str(exp.minimum_rate)}
        elif exp.kind == "accepted_values" and any(type(v) is not str for v in exp.values):
            unsupported.append({"rule_id": rule.id, "reason": "Typed non-string/mixed categories need a provider-specific conformance mapping; do not coerce boolean/integer/string categories."})
            continue
        elif exp.kind == "accepted_values" and exp.allow_null:
            test, column, arguments = "accepted_values", exp.column, {"values": exp.values}
        elif exp.kind == "accepted_values":
            test, column, arguments = "quality_accepted_values", exp.column, {"values": exp.values}
        elif exp.kind == "relationship" and not exp.allow_null and exp.maximum_orphan_rate == 0 and exp.require_unique_parent:
            test, column, arguments = "quality_relationship", exp.column, {"to": f"ref('{exp.parent_dataset}')", "field": exp.parent_column}
        elif exp.kind == "schema":
            # Model contracts enforce column types; nullable actual values are separately data-tested.
            unsupported.append({"rule_id": rule.id, "reason": "dbt model contract handles schema at build, not a standalone row test; result must be mapped explicitly."})
            continue
        else:
            unsupported.append({"rule_id": rule.id, "reason": "No exact export mapping in this slice; run the core deterministic evaluator."})
            continue
        body = {"config": config}
        if arguments:
            body["arguments"] = arguments
        (column_tests[column] if column else model_tests).append({test: body})
    dtype = {"STRING": "varchar", "INTEGER": "bigint", "DECIMAL": "decimal", "TIMESTAMP": "timestamptz", "BOOLEAN": "boolean"}
    columns = [{"name": c.name, "data_type": f"decimal({c.precision},{c.scale})" if c.data_type == "DECIMAL" else dtype[c.data_type],
                "description": c.description, "data_tests": column_tests[c.name]} for c in contract.columns]
    document = {"version": 2, "models": [{"name": contract.dataset_id, "description": contract.semantic_meaning,
                  "config": {"contract": {"enforced": True}, "meta": {"data_contract_id": contract.id}},
                  "columns": columns, "data_tests": model_tests}]}
    return {"contract_version": "dbt-quality-export-v1", "yaml": yaml.safe_dump(document, sort_keys=False),
            "document": document, "unsupported": unsupported,
            "required_macros": ["quality_unique_key", "quality_completeness", "quality_accepted_values", "quality_relationship"],
            "note": "Uses data_tests/arguments (dbt Core 1.10.5+). Copy supplied macros. Recorded dbt statuses have provider semantics: empty row checks may pass and failure counts may be groups. The core engine supplies UNKNOWN/volume/schema evidence for its gate. Blocking is separate from dbt severity."}


def dbt_result(rule: QualityRule, raw: dict | None, executed_at: str, run_id: str, fingerprint: str) -> ValidationResult:
    """Normalize one explicitly bound recorded dbt test. Generic failure counts may be groups."""
    aware(executed_at)
    reported = raw.get("status", "missing") if raw else "missing"
    status = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "error": "UNKNOWN", "skipped": "UNKNOWN"}.get(reported, "UNKNOWN")
    failures = raw.get("failures") if raw else None
    malformed_count = raw is not None and "failures" in raw and failures is not None and (type(failures) is not int or failures < 0)
    if failures is not None and (type(failures) is not int or failures < 0):
        failures = None
    if not raw or malformed_count or raw.get("quality_rule_id") != rule.id or (reported == "pass" and failures not in (0, None)):
        status = "UNKNOWN"
    return ValidationResult(rule_id=rule.id, target_id=rule.target, status=status,
        expected=rule.expectation.model_dump(mode="json"), actual={"dbt_reported_status": reported, "dbt_failures": failures},
        failed_rows=None, total_rows=None, failure_rate=None, severity=rule.severity, blocking=rule.blocking,
        executed_at=executed_at, run_id=run_id, input_fingerprint=fingerprint,
        evidence=Evidence(source="recorded_dbt_test", method="explicit quality_rule_id binding",
                          message="Recorded dbt result; failures may count duplicate groups rather than dataset rows. This does not rerun data validation.",
                          metrics={"reported_failures": failures, "unique_id": raw.get("unique_id") if raw else None}))


def gx_design(rule: QualityRule) -> dict:
    """Optional GX 1.x mapping design; unsupported semantics remain visible."""
    exp = rule.expectation
    mapping = None
    if exp.kind == "not_null":
        mapping = {"type": "ExpectColumnValuesToNotBeNull", "kwargs": {"column": exp.column, "mostly": str(exp.minimum_rate)}}
    elif exp.kind == "unique" and len(exp.columns) == 1:
        mapping = {"type": "ExpectColumnValuesToBeUnique", "kwargs": {"column": exp.columns[0]}}
    elif exp.kind == "accepted_values":
        mapping = {"type": "ExpectColumnValuesToBeInSet", "kwargs": {"column": exp.column, "value_set": exp.values}}
    return {"supported_design": mapping is not None, "mapping": mapping, "executed": False,
            "note": "Optional adapter design only. GX NULL/mostly/count semantics must be reconciled and conformance-tested before a gate trusts its result. Use the core engine now."}
