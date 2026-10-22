import pytest

from app.analytics import report_csv
from app.data_loader import ROOT
from app.qualtrics import parse_qualtrics, provided_report


def test_aggregate_import_admin_only_and_separate_source(client):
    content = (ROOT / "data/qualtrics_template.csv").read_text()
    body = {"csv_text": content, "synthetic_demo": True, "authorized_aggregate": True}
    assert client.post("/api/admin/qualtrics", json=body).status_code == 403
    client.headers["X-Demo-Key"] = "demo-admin"
    assert client.post("/api/admin/qualtrics", json=body).json()["rows"] == 3
    result = client.post(
        "/api/chat",
        json={"session_id": "q", "message": "Show Qualtrics engagement for Sales"},
    ).json()
    assert result["report"]["source"]["id"] == "qualtrics"
    assert result["report"]["departments"][0]["employees"] is None
    assert result["report"]["departments"][0]["metrics"]["engagement"]["value"] == 72.5
    assert "Provided scores" in result["report"]["source"]["scoring"]
    ibm = client.post(
        "/api/report", json={"department": "Sales", "metrics": ["job_satisfaction"]}
    ).json()
    assert (
        ibm["report"]["departments"][0]["metrics"]["job_satisfaction"]["value"] == 61.4
    )
    assert (
        client.post(
            "/api/admin/qualtrics", json={**body, "synthetic_demo": False}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "replacement",
    [
        ("72.5", "nan"),
        ("72.5", "101"),
        (",40,", ",-2,"),
        ("Sales,", "Marketing,"),
        ("ScoringMethodology", "WrongHeader"),
    ],
)
def test_bad_import_rejected(replacement):
    content = (ROOT / "data/qualtrics_template.csv").read_text()
    with pytest.raises(ValueError):
        parse_qualtrics(content.replace(*replacement))


def test_missing_metric_and_small_groups_never_filled():
    content = (ROOT / "data/qualtrics_template.csv").read_text().replace(",40,", ",3,")
    imported = parse_qualtrics(content)
    result = provided_report(imported, ["Sales"], ["engagement"])
    assert result["departments"][0]["metrics"]["engagement"]["value"] is None
    with pytest.raises(ValueError):
        provided_report(imported, ["Sales"], ["overtime"])


def test_imported_spreadsheet_formula_is_neutralized_on_export():
    content = (ROOT / "data/qualtrics_template.csv").read_text()
    lines = content.splitlines()
    fields = lines[1].split(",")
    fields[-1] = "=1+1"
    lines[1] = ",".join(fields)
    report = provided_report(
        parse_qualtrics("\n".join(lines)), ["Sales"], ["engagement"]
    )
    assert "'=1+1" in report_csv(report)
