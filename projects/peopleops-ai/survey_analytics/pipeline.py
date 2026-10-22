"""Small durable Bronze / Silver / Gold pipeline, independent of the HR app."""

import hashlib
import json
import sqlite3
import statistics
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .cohort import DEPARTMENTS, SURVEY_ID, cohort_fixture
from .fixture import export_fixture

METRIC_VERSION = "survey-metrics-v1"
MIN_GROUP = 5  # Demonstration rule, not an enterprise privacy guarantee.


def canonical(value):
    """Encode JSON consistently so identical exports have identical hashes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    """Give a JSON value a stable SHA-256 identifier."""
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@contextmanager
def connect(path):
    """Open local SQLite and create the three layers if they do not exist."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS bronze_batches (
          batch_id TEXT PRIMARY KEY, payload TEXT NOT NULL, ingested_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bronze_responses (
          batch_id TEXT, content_hash TEXT, response_id TEXT, payload TEXT NOT NULL,
          PRIMARY KEY(batch_id, content_hash));
        CREATE TABLE IF NOT EXISTS silver_responses (
          batch_id TEXT, response_id TEXT, content_hash TEXT, payload TEXT NOT NULL,
          PRIMARY KEY(batch_id, response_id));
        CREATE TABLE IF NOT EXISTS quarantine (
          batch_id TEXT, response_id TEXT, reason TEXT,
          PRIMARY KEY(batch_id, response_id));
        CREATE TABLE IF NOT EXISTS stages (
          batch_id TEXT, stage TEXT, result TEXT NOT NULL,
          PRIMARY KEY(batch_id, stage));
        CREATE TABLE IF NOT EXISTS gold_snapshots (
          batch_id TEXT, metric_version TEXT, payload TEXT NOT NULL,
          PRIMARY KEY(batch_id, metric_version));
    """)
    try:
        with db:
            yield db
    finally:
        db.close()


def cached(db, batch_id, stage):
    """Read the result of an already committed stage for safe retries."""
    row = db.execute(
        "SELECT result FROM stages WHERE batch_id=? AND stage=?", (batch_id, stage)
    ).fetchone()
    return json.loads(row[0]) if row else None


def save_stage(db, batch_id, stage, result):
    """Commit a stage result in the same transaction as its data changes."""
    db.execute(
        "INSERT INTO stages VALUES (?, ?, ?)", (batch_id, stage, canonical(result))
    )
    return result


def ingest_bronze(path, payload):
    """Keep the exact export and unique raw versions without overwriting history."""
    # This demo intentionally accepts only its server-owned fixture, never personal data.
    if payload != export_fixture() and payload != cohort_fixture():
        raise ValueError("Only the fixed synthetic export is accepted by this demo")
    batch_id = digest(payload)
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        previous = cached(db, batch_id, "bronze")
        if previous:
            return {**previous, "replayed": True}
        db.execute(
            "INSERT INTO bronze_batches VALUES (?, ?, ?)",
            (batch_id, canonical(payload), datetime.now(UTC).isoformat()),
        )
        for row in payload["responses"]:
            db.execute(
                "INSERT OR IGNORE INTO bronze_responses VALUES (?, ?, ?, ?)",
                (batch_id, digest(row), row["responseId"], canonical(row)),
            )
        count = db.execute(
            "SELECT COUNT(*) FROM bronze_responses WHERE batch_id=?", (batch_id,)
        ).fetchone()[0]
        return save_stage(
            db,
            batch_id,
            "bronze",
            {
                "batch_id": batch_id,
                "stage": "bronze",
                "synthetic": True,
                "raw_deliveries": len(payload["responses"]),
                "unique_versions": count,
                "duplicate_deliveries": len(payload["responses"]) - count,
                "replayed": False,
            },
        )


def validate_response(row):
    """Validate types, UTC timestamps, and score ranges without filling missing answers."""
    values = row["values"]
    if not isinstance(row.get("responseId"), str) or not row["responseId"]:
        raise ValueError("missing response ID")
    recorded = datetime.fromisoformat(values["recordedDate"])
    if recorded.tzinfo is None or recorded.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    if type(values["finished"]) is not bool:
        raise ValueError("finished must be boolean")
    if values["department"] not in DEPARTMENTS:
        raise ValueError("unknown department")
    for key, low, high in [("Q_ENGAGEMENT", 1, 5), ("Q_CSAT", 1, 5), ("Q_ENPS", 0, 10)]:
        score = values[key]
        if score is not None and (type(score) is not int or not low <= score <= high):
            raise ValueError(f"{key} outside {low}..{high}")
    if (
        type(values["durationSeconds"]) is not int
        or not 0 <= values["durationSeconds"] <= 86400
    ):
        raise ValueError("invalid duration")
    return {
        "response_id": row["responseId"],
        "recorded_at": recorded.isoformat(),
        "department": values["department"],
        "finished": values["finished"],
        "engagement": values["Q_ENGAGEMENT"],
        "csat": values["Q_CSAT"],
        "enps": values["Q_ENPS"],
        "duration_seconds": values["durationSeconds"],
    }


def transform_silver(path, batch_id):
    """Select the latest response version first, then validate or quarantine it."""
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        previous = cached(db, batch_id, "silver")
        if previous:
            return {**previous, "replayed": True}
        bronze = cached(db, batch_id, "bronze")
        if not bronze:
            raise ValueError("Bronze must finish before Silver")
        groups = {}
        for item in db.execute(
            "SELECT * FROM bronze_responses WHERE batch_id=?", (batch_id,)
        ):
            groups.setdefault(item["response_id"], []).append(
                json.loads(item["payload"])
            )
        accepted = rejected = 0
        for response_id, versions in groups.items():
            try:
                # No fallback to a previously valid revision when the latest is invalid.
                ordered = sorted(
                    versions,
                    key=lambda r: datetime.fromisoformat(r["values"]["recordedDate"]),
                )
                latest = ordered[-1]
                if (
                    len(ordered) > 1
                    and ordered[-2]["values"]["recordedDate"]
                    == latest["values"]["recordedDate"]
                ):
                    raise ValueError("conflicting versions at the same timestamp")
                clean = validate_response(latest)
                db.execute(
                    "INSERT INTO silver_responses VALUES (?, ?, ?, ?)",
                    (batch_id, response_id, digest(latest), canonical(clean)),
                )
                accepted += 1
            except (ValueError, KeyError, TypeError) as error:
                db.execute(
                    "INSERT INTO quarantine VALUES (?, ?, ?)",
                    (batch_id, response_id, str(error)),
                )
                rejected += 1
        return save_stage(
            db,
            batch_id,
            "silver",
            {
                "batch_id": batch_id,
                "stage": "silver",
                "synthetic": True,
                "accepted_responses": accepted,
                "quarantined_responses": rejected,
                "superseded_versions": bronze["unique_versions"] - len(groups),
                "replayed": False,
                "quarantine": [
                    dict(r)
                    for r in db.execute(
                        "SELECT response_id, reason FROM quarantine WHERE batch_id=?",
                        (batch_id,),
                    )
                ],
            },
        )


def metric(numerator, denominator, unit="percent"):
    """Return a value and its denominator; empty groups produce null, never zero."""
    return {
        "value": round(numerator / denominator * (100 if unit == "percent" else 1), 2)
        if denominator
        else None,
        "numerator": numerator,
        "denominator": denominator,
        "unit": unit,
    }


def score_metrics(rows):
    """Compute survey scores using only completed responses with an answer to that question."""
    completed = [r for r in rows if r["finished"]]
    eng = [r["engagement"] for r in completed if r["engagement"] is not None]
    csat = [r["csat"] for r in completed if r["csat"] is not None]
    enps = [r["enps"] for r in completed if r["enps"] is not None]
    return {
        "engagement_mean": metric(sum(eng), len(eng), "score_1_to_5"),
        "engagement_favorable": metric(sum(x >= 4 for x in eng), len(eng)),
        "csat_top_two_box": metric(sum(x >= 4 for x in csat), len(csat)),
        "enps": {
            **metric(sum(x >= 9 for x in enps) - sum(x <= 6 for x in enps), len(enps)),
            "unit": "points_-100_to_100",
            "promoters": sum(x >= 9 for x in enps),
            "detractors": sum(x <= 6 for x in enps),
        },
        "median_completion_seconds": statistics.median(
            r["duration_seconds"] for r in completed
        )
        if completed
        else None,
    }


def publish_gold(path, batch_id):
    """Publish an atomic, versioned aggregate snapshot with quality and lineage evidence."""
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        source = db.execute(
            "SELECT payload FROM bronze_batches WHERE batch_id=?", (batch_id,)
        ).fetchone()
        if not source:
            raise ValueError("Silver must finish before Gold")
        source_payload = json.loads(source[0])
        version = (
            "survey-metrics-v2"
            if source_payload["survey_id"] == SURVEY_ID
            else METRIC_VERSION
        )
        previous = db.execute(
            "SELECT payload FROM gold_snapshots WHERE batch_id=? AND metric_version=?",
            (batch_id, version),
        ).fetchone()
        if previous:
            return {**json.loads(previous[0]), "replayed": True}
        silver = cached(db, batch_id, "silver")
        if not silver:
            raise ValueError("Silver must finish before Gold")
        bronze = cached(db, batch_id, "bronze")
        payload = json.loads(
            db.execute(
                "SELECT payload FROM bronze_batches WHERE batch_id=?", (batch_id,)
            ).fetchone()[0]
        )
        rows = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT payload FROM silver_responses WHERE batch_id=? ORDER BY response_id",
                (batch_id,),
            )
        ]
        completed = sum(r["finished"] for r in rows)
        segments = []
        # Suppress every department slice when any nonempty department is small.
        # This prevents subtracting a visible department from the overall total.
        # Per-question sample counts must also meet the threshold.
        groups = {
            dept: [r for r in rows if r["department"] == dept]
            for dept in sorted({r["department"] for r in rows})
        }
        unsafe = any(
            sum(r["finished"] for r in group) < MIN_GROUP
            or any(
                sum(r["finished"] and r[key] is not None for r in group) < MIN_GROUP
                for key in ("engagement", "csat", "enps")
            )
            for group in groups.values()
        )
        if not unsafe:
            segments = [
                {
                    "department": dept,
                    "counts": {
                        "invited": payload.get("department_roster", {}).get(dept),
                        "valid_started": len(group),
                        "completed": sum(r["finished"] for r in group),
                    },
                    "metrics": score_metrics(group),
                }
                for dept, group in groups.items()
            ]
        overall_metrics = score_metrics(rows)
        if payload["survey_id"] == SURVEY_ID:
            for metrics in [overall_metrics, *(s["metrics"] for s in segments)]:
                mean = metrics["engagement_mean"]
                metrics["experience_score"] = metric(
                    mean["numerator"] * 20, mean["denominator"], "score_0_to_100"
                )
        result = {
            "batch_id": batch_id,
            "stage": "gold",
            "status": "ready",
            "synthetic": True,
            "survey_id": payload["survey_id"],
            "cohort_id": payload["cohort_id"],
            "metric_version": version,
            "published_at": datetime.now(UTC).isoformat(),
            "replayed": False,
            "counts": {
                "invited": payload["invited_count"],
                "valid_started": len(rows),
                "completed": completed,
            },
            "metrics": {
                "response_rate": metric(completed, payload["invited_count"]),
                "completion_rate": metric(completed, len(rows)),
                **overall_metrics,
            },
            "department_breakdown": segments,
            "privacy": {
                "minimum_completed_and_question_answers": MIN_GROUP,
                "department_slices_suppressed": unsafe,
                "reason": "All department slices withheld when any group/question is below 5; avoids subtraction disclosure"
                if unsafe
                else None,
            },
            "quality": {
                k: v
                for k, v in {**bronze, **silver}.items()
                if k
                in {
                    "raw_deliveries",
                    "unique_versions",
                    "duplicate_deliveries",
                    "accepted_responses",
                    "quarantined_responses",
                    "superseded_versions",
                }
            },
            "lineage": {
                "bronze_table": "bronze_responses",
                "silver_table": "silver_responses",
                "gold_table": "gold_snapshots",
                "source": "local fixed Qualtrics-shaped export; no external connection",
                "source_sha256": batch_id,
            },
        }
        db.execute(
            "INSERT INTO gold_snapshots VALUES (?, ?, ?)",
            (batch_id, version, canonical(result)),
        )
        return result


def inspect_layers(path, batch_id=None):
    """Show row counts and saved Gold snapshots without returning individual answers."""
    with connect(path) as db:
        tables = [
            "bronze_batches",
            "bronze_responses",
            "silver_responses",
            "quarantine",
            "gold_snapshots",
        ]
        where, params = (" WHERE batch_id=?", (batch_id,)) if batch_id else ("", ())
        counts = {
            table: db.execute(
                f"SELECT COUNT(*) FROM {table}" + where, params
            ).fetchone()[0]
            for table in tables
        }
        snapshots = [
            json.loads(row[0])
            for row in db.execute(
                "SELECT payload FROM gold_snapshots" + where + " ORDER BY rowid DESC",
                params,
            )
        ]
    return {"synthetic": True, "tables": counts, "gold": snapshots}
