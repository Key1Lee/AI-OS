"""Optional, explicit import of provided department scores; never blend with IBM."""

import csv
import io

from .analytics import MIN_GROUP, describe_report
from .models import DEPARTMENTS

COLUMNS = [
    "Department",
    "SurveyName",
    "SurveyPeriod",
    "Metric",
    "Score",
    "RespondentCount",
    "ScoringMethodology",
]
ALLOWED = {
    "job_satisfaction",
    "work_life_balance",
    "attrition",
    "overtime",
    "engagement",
}


def parse_qualtrics(csv_text):
    """Validate one synthetic aggregate survey and keep its supplied methodology intact."""
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    if reader.fieldnames != COLUMNS:
        raise ValueError(
            "CSV headers must exactly match the provided Qualtrics template"
        )
    rows, seen, surveys = [], set(), set()
    for row in reader:
        if (
            len(rows) >= 500
            or None in row
            or any(value is None for value in row.values())
        ):
            raise ValueError(
                "CSV has malformed rows or exceeds 500 department-metric rows"
            )
        row = {key: value.strip() for key, value in row.items()}
        if row["Department"] not in DEPARTMENTS or row["Metric"] not in ALLOWED:
            raise ValueError("Unsupported department or metric in CSV")
        if not all(
            1 <= len(row[key]) <= 500
            for key in ("SurveyName", "SurveyPeriod", "ScoringMethodology")
        ):
            raise ValueError("Survey name, period and scoring methodology are required")
        # Dates or documented text periods are accepted exactly as supplied; none is invented.
        try:
            score = float(row["Score"])
            count = int(row["RespondentCount"])
        except ValueError as error:
            raise ValueError(
                "Scores must be numeric and counts must be integers"
            ) from error
        if not 0 <= score <= 100 or count < 0:
            raise ValueError(
                "Scores must be finite percentages 0–100 and counts nonnegative"
            )
        identity = (row["Department"], row["Metric"])
        if identity in seen:
            raise ValueError("Duplicate department-metric row")
        seen.add(identity)
        surveys.add((row["SurveyName"], row["SurveyPeriod"]))
        rows.append({**row, "Score": score, "RespondentCount": count})
    if not rows or len(surveys) != 1:
        raise ValueError("Import exactly one nonempty survey and period at a time")
    return {
        "rows": rows,
        "name": rows[0]["SurveyName"],
        "period": rows[0]["SurveyPeriod"],
    }


def provided_report(imported, departments, metrics):
    """Return provided aggregates with source labels; do not recompute or fill missing scores."""
    rows = []
    for department in departments:
        available = {
            row["Metric"]: row
            for row in imported["rows"]
            if row["Department"] == department
        }
        if any(key not in available for key in metrics):
            raise ValueError(
                "Requested department or metric is absent from the imported survey"
            )
        values = {}
        for key in metrics:
            row = available[key]
            suppressed = row["RespondentCount"] < MIN_GROUP
            values[key] = {
                "key": key,
                "label": key.replace("_", " ").title(),
                "value": None if suppressed else round(row["Score"], 1),
                "denominator": None if suppressed else row["RespondentCount"],
                "average": None,
                "numerator": None,
                "status": "suppressed" if suppressed else "provided",
                "formula": row["ScoringMethodology"],
                "kind": "provided",
            }
        rows.append(
            {
                "department": department,
                "employees": None,
                "status": "provided",
                "metrics": values,
            }
        )
    return {
        "title": "Qualtrics CSV — Provided department scores",
        "source": {
            "id": "qualtrics",
            "label": "Qualtrics-format CSV · synthetic provided aggregates",
            "survey_name": imported["name"],
            "survey_period": imported["period"],
            "synthetic": True,
            "scoring": "Provided scores, not recomputed; source authenticity is not verified by this demo",
        },
        "metrics": metrics,
        "departments": rows,
        "summary": describe_report(rows, metrics),
        "limitations": "Synthetic import demonstration only. Provided scoring definitions apply; IBM proxies are not mixed into this report. Employee totals are not inferred from question counts.",
    }
