import csv
import io

import pandas as pd
import pytest

from app.analytics import METRICS, build_report, calculate_metric, report_csv
from app.data_loader import ROOT, load_data, validate_data


def test_pinned_ibm_population(data):
    assert len(data) == data.EmployeeNumber.nunique() == 1470
    assert data.groupby("Department").size().to_dict() == {
        "Sales": 446,
        "Research & Development": 961,
        "Human Resources": 63,
    }


@pytest.mark.parametrize(
    "department,key,column,numerator,denominator,expected",
    [
        ("Sales", "job_satisfaction", "JobSatisfaction", 274, 446, 61.4),
        (
            "Research & Development",
            "work_life_balance",
            "WorkLifeBalance",
            666,
            961,
            69.3,
        ),
        ("Human Resources", "attrition", "Attrition", 12, 63, 19.0),
        ("Sales", "overtime", "OverTime", 128, 446, 28.7),
    ],
)
def test_independent_csv_counts_and_scoring(
    data, department, key, column, numerator, denominator, expected
):
    with (ROOT / "data/ibm_hr.csv").open() as stream:
        rows = [
            row for row in csv.DictReader(stream) if row["Department"] == department
        ]
    favorable = (
        sum(int(row[column]) >= 3 for row in rows)
        if key in ("job_satisfaction", "work_life_balance")
        else sum(row[column] == "Yes" for row in rows)
    )
    assert (favorable, len(rows)) == (numerator, denominator)
    result = build_report(data, [department], [key])["departments"][0]["metrics"][key]
    assert (result["numerator"], result["denominator"], result["value"]) == (
        numerator,
        denominator,
        expected,
    )


def test_nulls_excluded_with_distinct_denominators(data):
    frame = data.copy()
    sales_indices = frame.index[frame.Department == "Sales"]
    frame.loc[sales_indices[:2], "JobSatisfaction"] = float("nan")
    frame.loc[sales_indices[:3], "WorkLifeBalance"] = float("nan")
    frame.loc[sales_indices[:4], "Attrition"] = None
    valid = validate_data(frame)
    metrics = build_report(valid, ["Sales"], list(METRICS))["departments"][0]["metrics"]
    assert [metrics[key]["denominator"] for key in METRICS] == [444, 443, 442, 446]
    assert metrics["job_satisfaction"]["missing"] == 2


def test_small_or_unanswered_groups_suppressed(data):
    assert calculate_metric(pd.Series([None] * 8), "job_satisfaction")["value"] is None
    result = build_report(
        data[data.Department == "Sales"].head(4), ["Sales"], ["attrition"]
    )
    assert result["departments"][0]["employees"] is None
    assert result["departments"][0]["metrics"]["attrition"]["denominator"] is None


@pytest.mark.parametrize(
    "mutation", ["empty", "missing", "duplicate", "score", "binary", "department"]
)
def test_malformed_data_rejected(data, mutation):
    frame = data.copy()
    if mutation == "empty":
        frame = frame.iloc[:0]
    if mutation == "missing":
        frame = frame.drop(columns=["JobSatisfaction"])
    if mutation == "duplicate":
        frame.loc[1, "EmployeeNumber"] = frame.loc[0, "EmployeeNumber"]
    if mutation == "score":
        frame.loc[0, "JobSatisfaction"] = 7
    if mutation == "binary":
        frame.loc[0, "Attrition"] = "Maybe"
    if mutation == "department":
        frame.loc[0, "Department"] = "Marketing"
    with pytest.raises(ValueError):
        validate_data(frame)


def test_checksum_and_missing_file_are_explicit(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("not the pinned dataset")
    with pytest.raises(ValueError, match="checksum"):
        load_data(path)
    with pytest.raises(ValueError, match="unavailable"):
        load_data(tmp_path / "absent.csv")


def test_csv_matches_only_displayed_aggregates(data):
    report = build_report(data, ["Sales", "Human Resources"], ["attrition"])
    rows = list(csv.DictReader(io.StringIO(report_csv(report))))
    assert len(rows) == 2
    assert rows[0]["percentage"] == "20.6"
    assert rows[1]["valid_observations"] == "63"
    assert "EmployeeNumber" not in report_csv(report)
    assert {row["metric"] for row in rows} == {"Observed attrition"}
