from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.models import InputKind
from app.openai_service import InterviewerUnavailable, OpenAIInterviewer
from tests.conftest import decision


def session_context():
    return {
        "target_role": "Senior Forward Deployed Engineer",
        "mode": "ASSESSMENT",
        "module": "Module 1 — Customer discovery and problem decomposition",
        "difficulty": 3,
        "scenario_id": "FDE-DISCOVERY-001-v1",
        "scenario": "Scenario",
        "current_question": "Question",
        "assistance_level": "none",
        "hints_used": 0,
        "failure_streak": 0,
        "previous_response_id": None,
    }


class StubResponses:
    def __init__(self, output):
        self.output = output
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.output


def test_openai_provider_uses_responses_parse_and_structured_schema(tmp_path):
    settings = Settings(project_root=tmp_path, database_path=tmp_path / "db", openai_api_key="test-key")
    provider = OpenAIInterviewer(settings)
    stub = StubResponses(
        SimpleNamespace(
            output_parsed=decision(),
            id="resp_test",
            usage=SimpleNamespace(model_dump=lambda mode: {"input_tokens": 10}),
        )
    )
    provider.client = SimpleNamespace(responses=stub)

    result = provider.evaluate(
        session=session_context(),
        input_kind=InputKind.ANSWER,
        content="Candidate answer",
        recent_turns=[],
        private_scenario_brief="Frozen facts",
        force_module_completion=False,
    )

    assert result.response_id == "resp_test"
    assert stub.kwargs["model"] == "gpt-6-sol"
    assert stub.kwargs["reasoning"] == {"effort": "medium"}
    assert stub.kwargs["text_format"].__name__ == "InterviewerDecision"
    assert stub.kwargs["store"] is True


def test_invalid_structured_output_is_rejected(tmp_path):
    settings = Settings(project_root=tmp_path, database_path=tmp_path / "db", openai_api_key="test-key")
    provider = OpenAIInterviewer(settings)
    provider.client = SimpleNamespace(
        responses=StubResponses(SimpleNamespace(output_parsed=None, id="resp_bad", usage=None))
    )

    with pytest.raises(InterviewerUnavailable, match="valid structured decision"):
        provider.evaluate(
            session=session_context(),
            input_kind=InputKind.ANSWER,
            content="Candidate answer",
            recent_turns=[],
            private_scenario_brief="Frozen facts",
            force_module_completion=False,
        )

