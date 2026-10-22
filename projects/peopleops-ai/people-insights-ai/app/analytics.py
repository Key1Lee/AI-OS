"""Deterministic department statistics and aggregate-only CSV exports."""

import csv
import io
import json

from .data_loader import ROOT

METRICS = {
    "job_satisfaction": {
        "label": "Job satisfaction",
        "column": "JobSatisfaction",
        "formula": "Count of valid scores ≥ 3 / valid 1–4 scores × 100",
        "kind": "favorable",
        "scale": "1–4",
    },
    "work_life_balance": {
        "label": "Work-life balance",
        "column": "WorkLifeBalance",
        "formula": "Count of valid scores ≥ 3 / valid 1–4 scores × 100",
        "kind": "favorable",
        "scale": "1–4",
    },
    "attrition": {
        "label": "Observed attrition",
        "column": "Attrition",
        "formula": "Yes / valid Yes-or-No indicators × 100",
        "kind": "observed",
        "scale": "Yes/No",
    },
    "overtime": {
        "label": "Employees working overtime",
        "column": "OverTime",
        "formula": "Yes / valid Yes-or-No indicators × 100",
        "kind": "observed",
        "scale": "Yes/No",
    },
}
MIN_GROUP = 5


def calculate_metric(series, metric):
    """Count valid observations, then calculate a percentage and an optional 1–4 mean."""
    definition = METRICS[metric]
    valid = series[
        series.isin(
            [1, 2, 3, 4] if definition["kind"] == "favorable" else ["Yes", "No"]
        )
    ]
    denominator = len(valid)
    numerator = int(
        (valid >= 3).sum()
        if definition["kind"] == "favorable"
        else (valid == "Yes").sum()
    )
    suppressed = denominator < MIN_GROUP
    return {
        "key": metric,
        "label": definition["label"],
        "unit": "percent",
        "value": round(numerator / denominator * 100, 1) if not suppressed else None,
        "average": round(float(valid.mean()), 2)
        if not suppressed and definition["kind"] == "favorable"
        else None,
        "numerator": numerator if not suppressed else None,
        "denominator": denominator if not suppressed else None,
        "missing": int(len(series) - denominator) if not suppressed else None,
        "formula": definition["formula"],
        "kind": definition["kind"],
        "status": "suppressed" if suppressed else "ready",
    }


def describe_report(rows, metric_keys):
    """Write short descriptive statements from calculated numbers, without causal claims."""
    if len(rows) == 1:
        row = rows[0]
        descriptions = []
        for key in metric_keys:
            metric = row["metrics"][key]
            if metric["value"] is not None:
                suffix = "% favorable" if metric["kind"] == "favorable" else "%"
                descriptions.append(
                    f"{metric['label']} is {metric['value']:.1f}{suffix} (n={metric['denominator']})"
                )
        if not descriptions:
            return "The requested scores are suppressed because there are fewer than 5 valid observations. No numerical result is inferred."
        return (
            "; ".join(descriptions)
            + ". These descriptive sample results do not establish causes or predict future departures."
        )
    descriptions = []
    for key in metric_keys:
        available = [row for row in rows if row["metrics"][key]["value"] is not None]
        if len(available) < 2:
            continue
        high = max(available, key=lambda row: row["metrics"][key]["value"])
        low = min(available, key=lambda row: row["metrics"][key]["value"])
        difference = high["metrics"][key]["value"] - low["metrics"][key]["value"]
        descriptions.append(
            f"{high['department']} is {difference:.1f} percentage points above {low['department']} on {high['metrics'][key]['label'].lower()}"
        )
    return (
        "; ".join(descriptions)
        + ". These are descriptive differences, not evidence of causes or statistical significance."
    )


def build_report(data, departments, metrics):
    """Filter to approved departments and return only their computed aggregates."""
    if not metrics or any(metric not in METRICS for metric in metrics):
        raise ValueError(
            "Unsupported IBM metric; engagement and EX25 are not in this dataset"
        )
    rows = []
    for department in dict.fromkeys(departments):
        selected = data[data["Department"] == department]
        if len(selected) < MIN_GROUP:
            rows.append(
                {
                    "department": department,
                    "employees": None,
                    "status": "suppressed",
                    "metrics": {
                        key: {
                            "key": key,
                            "label": METRICS[key]["label"],
                            "value": None,
                            "average": None,
                            "denominator": None,
                            "numerator": None,
                            "formula": METRICS[key]["formula"],
                            "status": "suppressed",
                            "kind": METRICS[key]["kind"],
                        }
                        for key in metrics
                    },
                }
            )
            continue
        rows.append(
            {
                "department": department,
                "employees": len(selected),
                "status": "ready",
                "metrics": {
                    key: calculate_metric(selected[METRICS[key]["column"]], key)
                    for key in metrics
                },
            }
        )
    source = json.loads((ROOT / "data/source.json").read_text())
    return {
        "title": (departments[0] if len(departments) == 1 else "Department comparison")
        + " — Employee Experience Report",
        "source": {
            "id": "ibm",
            "label": "IBM HR Analytics · synthetic sample",
            "synthetic": True,
            "rows": len(data),
            "sha256": source["sha256"],
            "url": source["source_url"],
            "survey_period": None,
            "scoring": "Computed IBM sample proxies; not an official Qualtrics EX25 score",
        },
        "metrics": list(dict.fromkeys(metrics)),
        "departments": rows,
        "summary": describe_report(rows, metrics),
        "limitations": "Single snapshot; no survey date or historical trend is supplied. Observed attrition is a sample indicator, not a resignation prediction. Minimum group and valid-answer size: 5.",
    }


def report_csv(report):
    """Export exactly the displayed department metrics, without employee records."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "source",
            "department",
            "employees",
            "metric",
            "percentage",
            "valid_observations",
            "numerator",
            "average_1_to_4",
            "status",
            "methodology",
            "survey_period",
        ]
    )
    for row in report["departments"]:
        for key in report["metrics"]:
            metric = row["metrics"][key]
            cells = [
                report["source"]["label"],
                row["department"],
                row["employees"],
                metric["label"],
                metric["value"],
                metric["denominator"],
                metric.get("numerator"),
                metric.get("average"),
                metric["status"],
                metric["formula"],
                report["source"].get("survey_period"),
            ]
            # Neutralize spreadsheet formula prefixes in administrator-provided descriptions.
            writer.writerow(
                [
                    "'" + value
                    if isinstance(value, str)
                    and value.lstrip().startswith(("=", "+", "-", "@"))
                    else value
                    for value in cells
                ]
            )
    return output.getvalue()
