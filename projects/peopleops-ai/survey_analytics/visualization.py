"""Generate portable visualizations and CSV from committed Gold aggregates only."""

import csv
import io
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from .cohort import SURVEY_ID
from .final_report import render_final_report
from .pipeline import connect

ASSETS = Path(__file__).parent / "dashboard"


def get_cohort_gold(path, batch_id=None, required=True):
    """Read a published cohort snapshot without deriving scores from browser or source data."""
    with connect(path) as db:
        sql = "SELECT payload FROM gold_snapshots WHERE json_extract(payload, '$.survey_id')=?"
        args = [SURVEY_ID]
        if batch_id:
            sql += " AND batch_id=?"
            args.append(batch_id)
        row = db.execute(sql + " ORDER BY rowid DESC LIMIT 1", args).fetchone()
    if not row:
        if required:
            raise ValueError(
                "Run the 5,000-employee n8n workflow to publish Gold first"
            )
        return None
    return json.loads(row[0])


def render_dashboard(gold, snapshot=False):
    """Embed aggregate data, CSS and JavaScript into a self-contained dashboard."""
    html = (ASSETS / "index.html").read_text()
    data = json.dumps({"gold": gold, "snapshot": snapshot}, allow_nan=False).replace(
        "<", "\\u003c"
    )
    return (
        html.replace("/*__STYLE__*/", (ASSETS / "style.css").read_text())
        .replace("/*__DATA__*/", "window.SURVEY_DATA=" + data + ";")
        .replace("/*__SCRIPT__*/", (ASSETS / "app.js").read_text())
    )


def publish_visualization(path, batch_id):
    """Write an offline HTML visualization and department CSV for a known Gold batch."""
    if not re.fullmatch(r"[0-9a-f]{64}", batch_id):
        raise ValueError("Invalid batch identifier")
    gold = get_cohort_gold(path, batch_id)
    if gold["counts"]["completed"] != 5000:
        raise ValueError("The complete 5,000-employee cohort is required")
    directory = Path(path).parent / "visualizations"
    directory.mkdir(parents=True, exist_ok=True)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "synthetic",
            "department",
            "invited",
            "responses",
            "experience_score_0_100",
            "engagement_answers",
            "csat_percent",
            "csat_answers",
            "enps_points",
            "enps_answers",
        ]
    )
    for segment in gold["department_breakdown"]:
        metrics = segment["metrics"]
        writer.writerow(
            [
                True,
                segment["department"],
                segment["counts"]["invited"],
                segment["counts"]["completed"],
                metrics["experience_score"]["value"],
                metrics["experience_score"]["denominator"],
                metrics["csat_top_two_box"]["value"],
                metrics["csat_top_two_box"]["denominator"],
                metrics["enps"]["value"],
                metrics["enps"]["denominator"],
            ]
        )
    files = {
        "html": directory / f"{batch_id}.html",
        "csv": directory / f"{batch_id}.csv",
    }
    # Replace complete files atomically so readers never see a partially written artifact.
    for extension, content in {
        "html": render_final_report(gold, snapshot=True),
        "csv": output.getvalue(),
    }.items():
        with NamedTemporaryFile(
            mode="w", dir=directory, suffix=".tmp", delete=False
        ) as temporary:
            temporary.write(content)
            pending = Path(temporary.name)
        pending.replace(files[extension])
    return {
        "status": "ready",
        "synthetic": True,
        "batch_id": batch_id,
        "employees": 5000,
        "departments": len(gold["department_breakdown"]),
        "dashboard_url": "http://127.0.0.1:8812/dashboard",
        "report_url": "http://127.0.0.1:8812/report",
        "downloads": {key: f"/analytics/export/{batch_id}/{key}" for key in files},
        "files": {key: str(value) for key, value in files.items()},
    }
