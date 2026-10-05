"""Runs only in the Quality sibling's Python environment; never changes it.

Its native Dataset contract permits 200 rows. Pack complete primary-key groups
into bounded shards so native uniqueness checks cover cross-input duplicates.
Partitioning and evidence aggregation belong to the Lab; rule evaluation stays
inside quality_system.
"""
from __future__ import annotations

import json
import sys

from quality_system.adapters import contract_from_modeling
from quality_system.contracts import AcceptedValues, Dataset, QualityRule, ValidateRequest, Volume
from quality_system.engine import validate_bundle

MAX_ROWS = 200


def shards_for(rows: list[dict]) -> list[list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each order must be a JSON object")
        key = (["missing"] if "order_id" not in row else
               [type(row["order_id"]).__name__, row["order_id"]])
        encoded = json.dumps(key, sort_keys=True, separators=(",", ":"), allow_nan=False)
        groups.setdefault(encoded, []).append(row)

    shards: list[list[dict]] = []
    current: list[dict] = []
    for key in sorted(groups):
        group = groups[key]
        if len(group) > MAX_ROWS:
            raise ValueError("A complete order_id group exceeds the native 200-row limit; validation is withheld")
        if current and len(current) + len(group) > MAX_ROWS:
            shards.append(current)
            current = []
        current.extend(group)
    if current or not shards:
        shards.append(current)
    if sum(map(len, shards)) != len(rows):
        raise ValueError("Native quality shards do not cover every input row")
    return shards


def validate(payload: dict) -> dict:
    rows = payload["orders"]
    if not isinstance(rows, list):
        raise ValueError("Orders must be a JSON array")
    contract = contract_from_modeling({
        "contract_version": "modeling-lab-v1", "dataset_id": "fct_orders",
        "fact_contract": {
            "grain": "completed order", "primary_key": ["order_id"],
            "owner": "AE Lab Commerce Analytics",
            "semantic_meaning": "Gross completed-order revenue before returns in USD; one current row per order.",
            "columns": [
                {"name": "order_id", "data_type": "VARCHAR", "nullable": False},
                {"name": "customer_id", "data_type": "VARCHAR", "nullable": False},
                {"name": "status", "data_type": "VARCHAR", "nullable": False},
                {"name": "order_amount", "data_type": "DECIMAL(18,2)", "nullable": False},
                {"name": "currency", "data_type": "VARCHAR", "nullable": False},
                {"name": "ordered_at", "data_type": "TIMESTAMP WITH TIME ZONE", "nullable": False},
            ],
        },
    })
    contract.currency = "USD"
    contract.rules.extend([
        QualityRule(id="completed_orders", name="Only completed orders enter this fact",
                    description="The declared gross revenue metric uses completed orders.",
                    target="fct_orders", dimension="validity",
                    expectation=AcceptedValues(column="status", values=["completed"])),
        QualityRule(id="usd_currency", name="Order currency is USD",
                    description="Do not combine incompatible currency measures.",
                    target="fct_orders", dimension="validity",
                    expectation=AcceptedValues(column="currency", values=["USD"])),
        QualityRule(id="shard_volume", name="Quality shard contains row evidence",
                    description="Every native shard must contain one to 200 rows.",
                    target="fct_orders", dimension="volume",
                    expectation=Volume(minimum=1, maximum=MAX_ROWS)),
    ])
    bundles, events, shards = [], [], []
    duplicate_extra, distinct_keys, duplicate_affected = [], [], []
    for index, shard in enumerate(shards_for(rows)):
        dataset = Dataset(id="fct_orders", columns=contract.columns, rows=shard,
                          loaded_at=payload["timestamp"], currency="USD")
        request = ValidateRequest(contract=contract, datasets={"fct_orders": dataset},
                                  executed_at=payload["timestamp"], run_id=payload["run_id"])
        bundle = validate_bundle(request).model_dump(mode="json")
        bundles.append(bundle)
        events.extend(bundle["events"])
        grain = next(result for result in bundle["results"] if result["rule_id"] == "contract_grain")
        metrics = grain["evidence"]["metrics"]
        duplicate_extra.append(metrics.get("duplicate_extra_rows"))
        distinct_keys.append(metrics.get("distinct_non_null_keys"))
        duplicate_affected.append(metrics.get("duplicate_affected_rows"))
        shards.append({"shard_id": f"quality-{index:04d}", "rows": len(shard),
                       "input_fingerprint": bundle["input_fingerprint"],
                       "gate_status": bundle["gate"]["status"]})
    gate_open = bool(rows) and all(bundle["gate"]["status"] == "OPEN" and
                                bundle["gate"]["publication"] == "ELIGIBLE" and
                                all(result["status"] == "PASS" for result in bundle["results"])
                                for bundle in bundles)

    def aggregate(values: list[int | None]) -> int | None:
        return sum(values) if all(value is not None for value in values) else None

    return {"status": "PASS" if gate_open else "FAIL", "gate_open": gate_open,
            "duplicate_extra": aggregate(duplicate_extra), "distinct_keys": aggregate(distinct_keys),
            "duplicate_affected": aggregate(duplicate_affected), "total_rows": len(rows),
            "validated_rows": sum(shard["rows"] for shard in shards),
            "results": bundles, "events": events, "shards": shards,
            "partition_policy": "whole typed order_id groups; complete coverage; at most 200 rows per native request"}


if __name__ == "__main__":
    json.dump(validate(json.load(sys.stdin)), sys.stdout, allow_nan=False)
