from fastapi.testclient import TestClient

from survey_analytics.api import create_app


def test_local_notifications_are_idempotent_and_reject_payload_leaks(tmp_path):
    with TestClient(create_app(tmp_path / "notifications.sqlite3")) as client:
        event = {
            "workflow_id": "qualtricsGoldFailure01",
            "execution_id": "42",
            "last_node": "Intentional checklist failure",
        }
        assert (
            client.post("/notifications/workflow-error", json=event).status_code == 200
        )
        assert (
            client.post("/notifications/workflow-error", json=event).status_code == 200
        )
        inbox = client.get("/notifications").json()
        assert len(inbox["notifications"]) == 1
        assert inbox["notifications"][0]["execution_id"] == "42"
        assert (
            client.post(
                "/notifications/workflow-error",
                json={**event, "stack": "private payload"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/notifications/workflow-error",
                json={**event, "workflow_id": "peopleopsPolicy01"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/notifications/workflow-error",
                json={**event, "last_node": "untrusted question"},
            ).status_code
            == 422
        )


def test_workflow_exports_keep_the_hr_app_out_of_mcp():
    from survey_analytics.build_workflow import (
        build,
        build_error_handler,
        build_failure_probe,
    )

    main = build()["settings"]
    assert main["timeSavedPerExecution"] == 10 and main["timeSavedMode"] == "fixed"
    assert main["errorWorkflow"] == "qualtricsGoldError01"
    assert main["availableInMCP"] is True
    assert build_error_handler()["settings"]["availableInMCP"] is False
    assert build_failure_probe()["settings"]["availableInMCP"] is False
