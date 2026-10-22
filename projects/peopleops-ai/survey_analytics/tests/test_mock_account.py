from fastapi.testclient import TestClient

from survey_analytics.api import create_app
from survey_analytics.build_workflow import build
from survey_analytics.fixture import export_fixture
from survey_analytics.mock_account import DEMO_API_TOKEN
from survey_analytics.pipeline import digest


def test_all_mock_source_routes_require_fake_token(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite3")) as client:
        export_id = digest(export_fixture())
        routes = [
            ("GET", "/mock-qualtrics/account"),
            ("POST", "/mock-qualtrics/exports"),
            ("GET", f"/mock-qualtrics/exports/{export_id}"),
            ("GET", f"/mock-qualtrics/exports/{export_id}/file"),
        ]
        for method, route in routes:
            assert client.request(method, route).status_code == 401
            assert (
                client.request(
                    method, route, headers={"X-API-TOKEN": "wrong"}
                ).status_code
                == 401
            )
            response = client.request(
                method, route, headers={"X-API-TOKEN": DEMO_API_TOKEN}
            )
            assert response.status_code == 200 and response.json()["synthetic"]
        assert (
            client.get(
                "/mock-qualtrics/account", headers={"X-API-TOKEN": DEMO_API_TOKEN}
            ).json()["real_qualtrics_connected"]
            is False
        )
        # Authentication failures do not ingest anything into the layers.
        assert client.get("/layers").json()["tables"]["bronze_batches"] == 0


def test_export_workflow_authenticates_each_source_request():
    nodes = {n["name"]: n for n in build()["nodes"]}
    for name in (
        "Start mock Qualtrics export",
        "Check export ready",
        "Download synthetic responses",
    ):
        assert nodes[name]["parameters"]["headerParameters"]["parameters"] == [
            {"name": "X-API-TOKEN", "value": DEMO_API_TOKEN}
        ]


def test_percentiles_and_bounds():
    import asyncio

    import pytest

    from survey_analytics.load_test import percentile, run_load

    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([8], 0.99) == 8
    with pytest.raises(ValueError, match="concurrent"):
        asyncio.run(run_load(500, 500))
