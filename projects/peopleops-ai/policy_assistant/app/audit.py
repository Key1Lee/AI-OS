"""Durable, allowlisted audit events and local aggregate operational measurements."""
import json
import logging
import math

FIELDS = {"request_id", "intent", "workflow", "decision", "status", "source_status", "attempts", "retrieval_ms", "tool_ms", "total_ms", "retrieved_count", "event", "failure_code"}
LOG = logging.getLogger("peopleops.enterprise.audit")


def configure_logging():
    """Emit one JSON message per audit event in the running application."""
    LOG.setLevel(logging.INFO)
    # HTTP clients otherwise log the resource URL, which contains synthetic IDs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    if not LOG.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOG.addHandler(handler)


def write_audit(conn, event):
    """Store and log operational fields only; reject any unapproved field rather than leaking it."""
    if set(event) - FIELDS:
        raise ValueError("Audit event contains non-allowlisted fields")
    encoded = json.dumps(event, sort_keys=True, allow_nan=False)
    conn.execute("INSERT INTO audits(request_id,event) VALUES(?,?)", (event["request_id"], encoded))
    LOG.info(encoded)


def percentile(values, fraction):
    if not values:
        return 0
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * fraction) - 1)]


def metrics(conn):
    """Report aggregate counts and p50/p95/p99 for measured local requests."""
    events = [json.loads(row[0]) for row in conn.execute("SELECT event FROM audits")]
    requests = [event for event in events if event.get("event") == "request_completed"]
    durations = [event["total_ms"] for event in requests]
    latest=conn.execute("SELECT created_at,report FROM ingestion_runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return {"requests": len(requests), "events": len(events), "unavailable": sum(e["status"] == "unavailable" for e in requests),
            "latency_ms": {"p50": percentile(durations, .5), "p95": percentile(durations, .95), "p99": percentile(durations, .99)},
            "index": {"last_ingestion_utc":latest["created_at"],"rejected_sources":len(json.loads(latest["report"])["rejected"])} if latest else None,
            "measurement_scope": "local synthetic mock requests; not a production SLA"}
