from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.models import (
    AssistanceLevel,
    CompetencyState,
    CompetencyUpdate,
    Correctness,
    RecordUpdates,
    WeaknessUpdate,
)
from app.openai_service import InterviewerUnavailable
from tests.conftest import FakeProvider, decision


def test_missing_api_key_is_visible_and_blocks_new_session(app_factory):
    client, _, _, _ = app_factory(api_key=None)

    config = client.get("/api/config")
    response = client.post("/api/sessions", json={"target_role": "Senior FDE"})

    assert config.status_code == 200
    assert config.json()["api_configured"] is False
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_session_starts_persists_and_submission_is_idempotent(app_factory, start_session):
    client, provider, database, _ = app_factory([decision("Which stakeholder owns the decision?")])
    session = start_session(client)
    request = {
        "request_id": "req_12345678",
        "kind": "answer",
        "content": "I would first identify the decision owner and define the breached workflow.",
    }

    first = client.post(f"/api/sessions/{session['id']}/submit", json=request)
    duplicate = client.post(f"/api/sessions/{session['id']}/submit", json=request)
    refreshed = client.get(f"/api/sessions/{session['id']}")

    assert first.status_code == 200
    assert first.json()["current_question"] == "Which stakeholder owns the decision?"
    assert duplicate.status_code == 200
    assert refreshed.json()["turn_number"] == 2
    assert len(provider.calls) == 1
    assert len(database.recent_turns(session["id"])) == 1


def test_hint_is_recorded_and_prevents_independent_demonstration(app_factory, start_session):
    update = RecordUpdates(
        competency_updates=[
            CompetencyUpdate(
                competency="Requirements clarification, discovery, ambiguous problem decomposition",
                proposed_state=CompetencyState.DEMONSTRATED,
                evidence="Candidate independently selected the highest-leverage unknowns.",
                difficulty=3,
                independent=True,
            )
        ],
        weakness_updates=[
            WeaknessUpdate(
                competency="Testing, verification and regression analysis",
                classification="Requirements Gap",
                evidence="No validation threshold was defined.",
                remediation="Define measurable validation thresholds in a different scenario.",
            )
        ],
        next_recommended_assessment="A materially different data-reconciliation module.",
    )
    client, _, _, project_root = app_factory(
        [
            decision("Consider the business decision this prediction changes.", assistance=AssistanceLevel.NONE),
            decision(
                "Module complete.",
                module_complete=True,
                correctness=Correctness.CORRECT,
                record_updates=update,
            ),
        ]
    )
    session = start_session(client)

    hinted = client.post(
        f"/api/sessions/{session['id']}/submit",
        json={"request_id": "req_hint0001", "kind": "hint", "content": "Give me a hint."},
    )
    completed = client.post(
        f"/api/sessions/{session['id']}/submit",
        json={"request_id": "req_end00001", "kind": "end_module", "content": "My final answer."},
    )
    dashboard = client.get("/api/dashboard").json()

    assert hinted.status_code == 200
    assert hinted.json()["hints_used"] == 1
    assert hinted.json()["assistance_level"] == "minor_hint"
    assert completed.status_code == 200
    assert completed.json()["status"] == "MODULE_COMPLETE"
    assert completed.json()["module_review"]["independent"] is False
    competency = next(
        item for item in dashboard["competencies"] if item["competency"].startswith("Requirements")
    )
    assert competency["state"] == "DEVELOPING"
    assert dashboard["weaknesses"][0]["status"] == "OPEN"
    assert list((project_root / "assessment" / "session-evidence").glob("A-001-*.md"))
    assert "No mastery has been demonstrated" in (
        project_root / "assessment" / "mastery-evidence.md"
    ).read_text()


def test_active_turn_cannot_mutate_competency_progress(app_factory, start_session):
    illicit = RecordUpdates(
        competency_updates=[
            CompetencyUpdate(
                competency="Requirements clarification, discovery, ambiguous problem decomposition",
                proposed_state=CompetencyState.DEMONSTRATED,
                evidence="Premature",
                difficulty=3,
                independent=True,
            )
        ]
    )
    client, _, _, _ = app_factory([decision(record_updates=illicit)])
    session = start_session(client)

    response = client.post(
        f"/api/sessions/{session['id']}/submit",
        json={"request_id": "req_active01", "kind": "answer", "content": "An incomplete answer."},
    )
    competency = client.get("/api/dashboard").json()["competencies"][0]

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert competency["state"] == "UNTESTED"


def test_pause_resume_and_invalid_transition(app_factory, start_session):
    client, _, _, _ = app_factory()
    session = start_session(client)

    paused = client.post(f"/api/sessions/{session['id']}/pause")
    rejected = client.post(
        f"/api/sessions/{session['id']}/submit",
        json={"request_id": "req_paused01", "kind": "answer", "content": "Should not run."},
    )
    resumed = client.post(f"/api/sessions/{session['id']}/resume")

    assert paused.json()["status"] == "PAUSED"
    assert rejected.status_code == 409
    assert resumed.json()["status"] == "ACTIVE"


def test_session_resumes_after_application_restart(app_factory, start_session):
    client, _, database, project_root = app_factory()
    session = start_session(client)
    paused = client.post(f"/api/sessions/{session['id']}/pause")
    assert paused.json()["status"] == "PAUSED"

    settings = Settings(
        project_root=project_root,
        database_path=database.path,
        openai_api_key="test-key",
    )
    restarted = TestClient(
        create_app(
            settings,
            provider=FakeProvider(),
            database=Database(database.path),
            require_api_key=True,
        ),
        base_url="http://127.0.0.1",
    )
    restarted.headers["X-Interview-Token"] = restarted.get("/api/config").json()["request_token"]

    loaded = restarted.get(f"/api/sessions/{session['id']}")
    resumed = restarted.post(f"/api/sessions/{session['id']}/resume")
    assert loaded.status_code == 200
    assert loaded.json()["status"] == "PAUSED"
    assert resumed.json()["status"] == "ACTIVE"


def test_failed_api_call_preserves_answer_and_retries_without_duplicate(app_factory, start_session):
    client, provider, database, _ = app_factory(
        [InterviewerUnavailable("OpenAI request timed out. The answer was saved; retry is safe."), decision()]
    )
    session = start_session(client)
    payload = {
        "request_id": "req_retry001",
        "kind": "answer",
        "content": "Persist this exact answer before calling the API.",
    }

    failed = client.post(f"/api/sessions/{session['id']}/submit", json=payload)
    saved = database.get_submission(payload["request_id"])
    retried = client.post(f"/api/sessions/{session['id']}/submit", json=payload)

    assert failed.status_code == 502
    assert saved["status"] == "FAILED"
    assert saved["content"] == payload["content"]
    assert retried.status_code == 200
    assert len(database.recent_turns(session["id"])) == 1
    assert len(provider.calls) == 2


def test_repeated_failure_triggers_difficulty_reduction(app_factory, start_session):
    failures = [
        decision(correctness=Correctness.INCORRECT),
        decision(correctness=Correctness.PARTIAL),
        decision(correctness=Correctness.INCORRECT),
    ]
    client, _, database, _ = app_factory(failures)
    session = start_session(client)

    for index in range(3):
        response = client.post(
            f"/api/sessions/{session['id']}/submit",
            json={
                "request_id": f"req_failure{index}",
                "kind": "answer",
                "content": f"Attempt {index}",
            },
        )
        assert response.status_code == 200

    stored = database.get_session(session["id"])
    last_decision = database.recent_turns(session["id"])[-1]["decision_json"]
    assert stored["failure_streak"] == 3
    assert stored["difficulty"] == 2
    assert "Prerequisite diagnosis" in last_decision


def test_completed_module_can_continue_only_after_evidence_sync(app_factory, start_session):
    client, _, _, _ = app_factory(
        [decision("Module complete", module_complete=True), decision("Write the expected data grain.")]
    )
    session = start_session(client)
    completed = client.post(
        f"/api/sessions/{session['id']}/submit",
        json={"request_id": "req_finish01", "kind": "end_module", "content": "Final."},
    )
    continued = client.post(
        f"/api/sessions/{session['id']}/continue", json={"request_id": "req_continue1"}
    )

    assert completed.status_code == 200
    assert continued.status_code == 200
    assert continued.json()["status"] == "ACTIVE"
    assert continued.json()["module"].startswith("Module 2")
    assert continued.json()["current_question"] == "Write the expected data grain."
