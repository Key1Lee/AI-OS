from __future__ import annotations

import shutil
from collections import deque
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.models import (
    AssistanceLevel,
    Correctness,
    DifficultyAdjustment,
    EvidenceRating,
    FeedbackVisibility,
    InteractionType,
    InterviewerDecision,
    NextAction,
    RecordUpdates,
)
from app.openai_service import InterviewerUnavailable, ProviderResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def decision(
    message: str = "What evidence would you request next?",
    *,
    module_complete: bool = False,
    assistance: AssistanceLevel = AssistanceLevel.NONE,
    correctness: Correctness = Correctness.PARTIAL,
    record_updates: RecordUpdates | None = None,
) -> InterviewerDecision:
    return InterviewerDecision(
        interviewer_message=message,
        interaction_type=(
            InteractionType.MODULE_EVALUATION if module_complete else InteractionType.FOLLOW_UP
        ),
        assessment_continues=not module_complete,
        module_complete=module_complete,
        new_constraints=[],
        competencies_tested=[
            "Requirements clarification, discovery, ambiguous problem decomposition"
        ],
        evidence_observed=["Candidate prioritized an observable workflow outcome."],
        assistance_level=assistance,
        answer_correctness=correctness,
        reasoning_quality=EvidenceRating.STRONG,
        communication_quality=EvidenceRating.STRONG,
        technical_depth=EvidenceRating.ACCEPTABLE,
        production_awareness=EvidenceRating.ACCEPTABLE,
        security_awareness=EvidenceRating.NOT_OBSERVED,
        testing_quality=EvidenceRating.NOT_OBSERVED,
        confidence=0.83,
        weaknesses_detected=["Validation plan was incomplete"] if module_complete else [],
        strengths_detected=["High-leverage discovery sequencing"] if module_complete else [],
        follow_up_strategy="Probe the highest-risk assumption.",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN,
        next_action=NextAction.COMPLETE_MODULE if module_complete else NextAction.CONTINUE,
        record_updates=record_updates or RecordUpdates(),
        feedback_visibility=(
            FeedbackVisibility.MODULE_SUMMARY if module_complete else FeedbackVisibility.WITHHELD
        ),
    )


class FakeProvider:
    def __init__(self, outcomes=None):
        self.outcomes = deque(outcomes or [])
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.popleft() if self.outcomes else decision()
        if isinstance(outcome, Exception):
            raise outcome
        return ProviderResult(
            decision=outcome,
            response_id=f"resp_{len(self.calls)}",
            model="gpt-6-sol",
            reasoning_effort="medium",
            usage={"input_tokens": 100, "output_tokens": 50},
            duration_ms=25,
        )


@pytest.fixture
def app_factory(tmp_path):
    created = []

    def factory(outcomes=None, *, api_key="test-key"):
        project_root = tmp_path / f"project-{len(created)}"
        project_root.mkdir()
        shutil.copytree(PROJECT_ROOT / "assessment", project_root / "assessment")
        settings = Settings(
            project_root=project_root,
            database_path=project_root / "data" / "test.db",
            openai_api_key=api_key,
        )
        database = Database(settings.database_path)
        provider = FakeProvider(outcomes)
        application = create_app(
            settings,
            provider=provider,
            database=database,
            require_api_key=True,
        )
        created.append((application, provider, database, project_root))
        client = TestClient(application, base_url="http://127.0.0.1")
        client.headers["X-Interview-Token"] = client.get("/api/config").json()["request_token"]
        return client, provider, database, project_root

    return factory


@pytest.fixture
def start_session():
    def start(client: TestClient):
        response = client.post(
            "/api/sessions", json={"target_role": "Senior Forward Deployed Engineer"}
        )
        assert response.status_code == 201
        return response.json()

    return start
