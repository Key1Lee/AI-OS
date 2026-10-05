from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from .contracts import Event, EventType, SCENARIO_ID

BASE_TIME = datetime(2026, 10, 3, 0, tzinfo=timezone.utc)
LINEAGE = {"source.orders": [], "orders_raw": ["source.orders"], "stg_orders": ["orders_raw"],
           "int_orders_enriched": ["stg_orders"], "fct_orders": ["int_orders_enriched"],
           "revenue": ["fct_orders"], "executive_dashboard": ["revenue"]}

def emit(record: dict, system: str, asset: str | None, event_type: EventType, status: str, metadata: dict | None = None):
    sequence = len(record["events"]) + 1
    event = Event(event_id=f"{record['run_id']}:{sequence}", timestamp=(BASE_TIME + timedelta(seconds=sequence)).isoformat(),
                  run_id=record["run_id"], scenario_id=SCENARIO_ID, system=system, asset=asset,
                  event_type=event_type, status=status, metadata=metadata or {},
                  upstream_assets=tuple(LINEAGE.get(asset, [])))
    record["events"].append(event.as_dict())

def mermaid(mode: str = "healthy", asset: str | None = None) -> str:
    if mode not in {"healthy", "failed", "recovered"}:
        raise ValueError("Unknown diagram mode")
    assets = set(LINEAGE)
    if asset:
        if asset not in assets:
            raise ValueError(f"Unknown asset {asset}")
        assets = set()
        def visit(node):
            assets.add(node)
            for parent in LINEAGE[node]:
                visit(parent)
        visit(asset)
    ids = {a: f"n{i}" for i, a in enumerate(LINEAGE)}
    labels = {"source.orders": "SOURCE: orders", "orders_raw": "INGESTION / ORCHESTRATION: orders_raw",
              "stg_orders": "TRANSFORMATION: stg_orders", "int_orders_enriched": "int_orders_enriched",
              "fct_orders": "WAREHOUSE: fct_orders", "revenue": "METRIC: revenue", "executive_dashboard": "DASHBOARD"}
    lines = ["flowchart TD"]
    for node in LINEAGE:
        if node in assets:
            lines.append(f'  {ids[node]}["{labels[node]}"]')
            for parent in LINEAGE[node]:
                lines.append(f"  {ids[parent]} --> {ids[node]}")
    if "fct_orders" in assets:
        lines.extend(['  q["QUALITY: order_id uniqueness"]', f"  {ids['fct_orders']} --> q"])
    lines.extend(["  classDef healthy fill:#dcfce7,stroke:#166534", "  classDef failed fill:#fee2e2,stroke:#b91c1c",
                  "  classDef impact fill:#fef3c7,stroke:#b45309", "  classDef recovery fill:#dbeafe,stroke:#1d4ed8"])
    for node in LINEAGE:
        if node not in assets:
            continue
        style = "healthy" if mode == "healthy" else "recovery" if mode == "recovered" else "failed" if node == "orders_raw" else "healthy" if node == "source.orders" else "impact"
        lines.append(f"  class {ids[node]} {style}")
    if "fct_orders" in assets:
        lines.append(f"  class q {'failed' if mode == 'failed' else 'healthy'}")
    return "\n".join(lines)

def export(record: dict, directory: Path):
    (directory / "evidence.json").write_text(json.dumps(record, indent=2) + "\n")
    (directory / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in record["events"]))
    for mode in ("healthy", "failed", "recovered"):
        (directory / f"{mode}.mmd").write_text(mermaid(mode) + "\n")

def openlineage(record: dict) -> list[dict]:
    """One parent job run; internal asset observations are OTHER, not false task runs."""
    mapping = {EventType.RUN_STARTED: "START", EventType.RUN_COMPLETED: "COMPLETE"}
    return [{"eventTime": e["timestamp"], "eventType": mapping.get(e["event_type"], "OTHER"),
             "producer": "https://example.invalid/ae-lab/0.1.0", "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent",
             "run": {"runId": record["run_id"]}, "job": {"namespace": "ae-lab", "name": SCENARIO_ID},
             "inputs": [{"namespace": "ae-lab/commerce", "name": a} for a in e["upstream_assets"]],
             "outputs": [{"namespace": "ae-lab/commerce", "name": e["asset"]}] if e["asset"] else []}
            for e in record["events"]]
