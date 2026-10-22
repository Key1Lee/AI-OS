from copy import deepcopy

from fastapi.testclient import TestClient

from survey_analytics.api import create_app
from survey_analytics.cohort import cohort_fixture
from survey_analytics.final_report import render_final_report
from survey_analytics.pipeline import ingest_bronze, publish_gold, transform_silver


def test_final_report_published_metrics_portable_download_and_discovery(tmp_path):
    path = tmp_path / "report.sqlite3"
    with TestClient(create_app(path)) as client:
        empty = client.get("/report")
        assert empty.status_code == 200
        assert "waiting for results" in empty.text
        assert "75.99" not in empty.text
        batch = ingest_bronze(path, cohort_fixture())["batch_id"]
        transform_silver(path, batch)
        gold = publish_gold(path, batch)
        report = client.get("/report")
        assert report.status_code == 200
        for expected in (
            "75.99",
            "68.56",
            "+5.60",
            "13.36",
            "4,865",
            "4,828",
            "4,879",
            "20–100",
            "survey-metrics-v2",
            "Every response, department size and score is simulated",
        ):
            assert expected in report.text
        assert report.text.count('<th scope="row">') == 10
        assert "EMP_SYNTH_" not in report.text and "R_SAM_SYNTH_" not in report.text
        assert "__CHART__" not in report.text
        download = client.get(f"/analytics/export/{batch}/html")
        assert "attachment" in download.headers["content-disposition"]
        assert "Department scorecard" in download.text
        assert "↓ Download report" not in download.text
        assert "@media print" in download.text
        for page in ("/guide", "/dashboard"):
            assert 'href="/report"' in client.get(page).text
        before = deepcopy(gold)
        render_final_report(gold)
        assert gold == before


def test_report_escapes_department_labels_and_derives_findings(tmp_path):
    path = tmp_path / "escape.sqlite3"
    batch = ingest_bronze(path, cohort_fixture())["batch_id"]
    transform_silver(path, batch)
    gold = publish_gold(path, batch)
    people = next(
        row for row in gold["department_breakdown"] if row["department"] == "People"
    )
    people["department"] = '<img src=x onerror="alert(1)">'
    people["metrics"]["experience_score"]["value"] = 90.0
    html = render_final_report(gold)
    assert "<img src=x" not in html
    assert "&lt;img" in html
    assert "20.41 points" in html
