from __future__ import annotations

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError
from pydantic import ValidationError

from training.application import TrainingApplication
from training.calibration import evaluate_for_calibration
from training.config import Settings
from training.content import load_questions
from training.deterministic import (
    DeterministicCheck,
    DeterministicReport,
    enforce_authoritative_results,
)
from training.llm import (
    LLMUnavailable,
    QwenEvaluator,
    ReasoningEvaluation,
    select_provider,
)
from training.models import Assistance, Evaluation, Mode, Outcome
from training.persistence import TrainingStore

from .helpers import ScriptedIO


def structured_payload(question_id: str, criterion_ids: list[str]) -> dict:
    return {
        "overall_score": 86,
        "verdict": "pass",
        "dimension_scores": {
            "correctness": 90,
            "reasoning": 88,
            "completeness": 82,
            "engineering_judgment": 87,
            "communication": 80,
            "production_awareness": 89,
        },
        "strengths": ["Connects the failure mechanism to the proposed control."],
        "weaknesses": [],
        "missed_concepts": [],
        "critical_errors": [],
        "unsupported_assumptions": [],
        "follow_up_questions": ["Which failure window remains after this design?"],
        "evidence": ["The answer explicitly identifies the shared object lifetime."],
        "rubric_evidence": [
            {
                "criterion_id": criterion_id,
                "status": "met",
                "evidence": [f"Concrete evidence for {criterion_id}"],
                "analysis": "The response demonstrates this requirement.",
            }
            for criterion_id in criterion_ids
        ],
        "evaluation_confidence": "high",
        "evaluator_provider": "untrusted-model-value",
        "evaluator_model": "untrusted-model-value",
    }


class FakeModels:
    def __init__(self, model: str):
        self.model = model

    def list(self, **kwargs):
        return SimpleNamespace(data=[SimpleNamespace(id=self.model)])


class FakeCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error

    def create(self, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(
            id="local-response-1",
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
        )


class FakeLocalClient:
    def __init__(self, model: str, content: str | None = None, error: Exception | None = None):
        self.models = FakeModels(model)
        self.chat = SimpleNamespace(completions=FakeCompletions(content, error))


def qwen_provider(tmp_path, content: str | None = None, error: Exception | None = None):
    settings = Settings(
        database_path=tmp_path / "training.db",
        evaluator_provider="qwen_local",
        qwen_model="Qwen3.8-27B-UD-Q4_KS-C256K",
    )
    return QwenEvaluator(
        settings,
        client=FakeLocalClient(settings.qwen_model, content=content, error=error),
    )


def test_structured_output_schema_validates_and_rejects_bad_scores():
    question = load_questions()[0]
    payload = structured_payload(question.id, [item.id for item in question.criteria])
    assert ReasoningEvaluation.model_validate(payload).overall_score == 86
    payload["overall_score"] = 101
    with pytest.raises(ValidationError):
        ReasoningEvaluation.model_validate(payload)


def test_qwen_returns_semantic_result_with_authoritative_metadata(tmp_path):
    question = load_questions()[0]
    payload = structured_payload(question.id, [item.id for item in question.criteria])
    provider = qwen_provider(tmp_path, json.dumps(payload))
    healthy, reason = provider.health_check()
    assert healthy is True and reason is None
    result = provider.evaluate(question, "A demonstrated explanation.", Mode.ASSESSMENT)
    assert result.outcome == Outcome.PASS
    assert result.evaluator_provider == "qwen_local"
    assert result.evaluator_model == "Qwen3.8-27B-UD-Q4_KS-C256K"
    assert result.evaluation_mode == "reasoning"
    assert result.dimension_scores["engineering_judgment"] == 87
    assert result.follow_up_questions == ("Which failure window remains after this design?",)


def test_qwen_invalid_json_is_rejected(tmp_path):
    provider = qwen_provider(tmp_path, "not-json")
    with pytest.raises(LLMUnavailable, match="invalid structured JSON"):
        provider.evaluate(load_questions()[0], "answer", Mode.DAILY)


def test_qwen_incomplete_rubric_evidence_is_rejected(tmp_path):
    question = load_questions()[0]
    payload = structured_payload(question.id, [question.criteria[0].id])
    provider = qwen_provider(tmp_path, json.dumps(payload))
    with pytest.raises(LLMUnavailable, match="rubric evidence"):
        provider.evaluate(question, "answer", Mode.DAILY)


def test_qwen_timeout_falls_back_without_crashing_assessment(tmp_path):
    timeout = APITimeoutError(httpx.Request("POST", "http://127.0.0.1/v1/chat/completions"))
    provider = qwen_provider(tmp_path, error=timeout)
    settings = Settings(
        database_path=tmp_path / "training.db",
        evaluator_provider="qwen_local",
        session_questions=1,
    )
    io = ScriptedIO(
        [
            "",
            "The mutable default is created once and shared across calls. Use None; test two calls for independent results.",
            "/submit",
        ]
    )
    assert TrainingApplication(settings, io, provider=provider).run() == 0
    assert "Reasoning evaluator unavailable" in io.transcript
    with TrainingStore(settings.database_path).connect() as connection:
        run = connection.execute(
            "SELECT provider, model, fallback_reason FROM evaluation_runs"
        ).fetchone()
    assert run["provider"] == "offline_fallback"
    assert run["model"] == "deterministic-rubric-v1"
    assert "Qwen" in run["fallback_reason"]
    assert TrainingStore(settings.database_path).competency("Python semantics")["independent_successes"] == 0
    assert "unassessed/diagnostic 1" in io.transcript
    store = TrainingStore(settings.database_path)
    with store.connect() as connection:
        attempt = connection.execute("SELECT evaluated_at FROM attempts WHERE id=1").fetchone()
        summary = json.loads(connection.execute("SELECT summary_json FROM sessions WHERE id=1").fetchone()[0])
    review = store.competency("Python semantics")["next_review_at"]
    assert datetime.fromisoformat(review) <= datetime.fromisoformat(attempt["evaluated_at"]) + timedelta(days=1)
    assert summary["assessed"] == 0 and summary["diagnostic"] == 1 and summary["pass"] == 0


def test_authoritative_deterministic_failure_overrides_model_pass(tmp_path):
    question = load_questions()[0]
    payload = structured_payload(question.id, [item.id for item in question.criteria])
    provider = qwen_provider(tmp_path, json.dumps(payload))
    report = DeterministicReport(
        version="test-v1",
        checks=(
            DeterministicCheck(
                name="sql_expected_rows",
                passed=False,
                authoritative=True,
                detail="Query returned incorrect rows.",
            ),
        ),
    )
    model_result = provider.evaluate_with_context(
        question, "plausible explanation", Mode.ASSESSMENT, report
    )
    final = enforce_authoritative_results(model_result, report)
    assert final.outcome == Outcome.FAIL
    assert final.score <= 0.39
    assert "sql_expected_rows" in final.critical_errors
    assert final.evaluator_provider == "qwen_local"


def test_qwen_primary_selected_in_auto_when_healthy(monkeypatch, tmp_path):
    class HealthyQwen:
        name = "qwen_local"

        def __init__(self, settings):
            self.model = settings.qwen_model

        def health_check(self):
            return True, None

    monkeypatch.setattr("training.llm.QwenEvaluator", HealthyQwen)
    settings = Settings(database_path=tmp_path / "db", evaluator_provider="auto")
    selection = select_provider(settings)
    assert selection.provider is not None
    assert selection.provider.name == "qwen_local"


def test_openai_primary_selected_only_when_explicit(monkeypatch, tmp_path):
    class FakeOpenAI:
        name = "openai"

        def __init__(self, settings):
            pass

    class HealthyQwen:
        name = "qwen_local"

        def __init__(self, settings):
            pass

        def health_check(self):
            return True, None

    monkeypatch.setattr("training.llm.OpenAIEvaluator", FakeOpenAI)
    monkeypatch.setattr("training.llm.QwenEvaluator", HealthyQwen)
    settings = Settings(database_path=tmp_path / "db", evaluator_provider="openai")
    selection = select_provider(settings)
    assert selection.provider is not None
    assert selection.provider.name == "openai -> qwen_local"
    assert selection.provider.providers[0].name == "openai"


def test_unreachable_qwen_selects_lexical_fallback(monkeypatch, tmp_path):
    class UnhealthyQwen:
        name = "qwen_local"

        def __init__(self, settings):
            pass

        def health_check(self):
            return False, "connection refused"

    monkeypatch.setattr("training.llm.QwenEvaluator", UnhealthyQwen)
    settings = Settings(database_path=tmp_path / "db", evaluator_provider="auto")
    selection = select_provider(settings)
    assert selection.provider is None
    assert selection.display_name == "offline fallback"
    assert selection.fallback_reason == "connection refused"


def test_primary_qwen_metadata_is_audited(tmp_path):
    question = load_questions()[0]
    payload = structured_payload(question.id, [item.id for item in question.criteria])
    provider = qwen_provider(tmp_path, json.dumps(payload))
    settings = Settings(
        database_path=tmp_path / "training.db",
        evaluator_provider="qwen_local",
        session_questions=1,
    )
    io = ScriptedIO(["", "A demonstrated explanation.", "/submit"])
    assert TrainingApplication(settings, io, provider=provider).run() == 0
    with TrainingStore(settings.database_path).connect() as connection:
        run = connection.execute("SELECT * FROM evaluation_runs").fetchone()
    assert run["provider"] == "qwen_local"
    assert run["model"] == "Qwen3.8-27B-UD-Q4_KS-C256K"
    assert run["evaluation_mode"] == "reasoning"
    assert json.loads(run["deterministic_json"])["version"] == "deterministic-v1"


def test_calibration_keeps_provider_results_separate_without_changing_mastery(tmp_path):
    question = load_questions()[0]
    settings = Settings(database_path=tmp_path / "training.db", llm_mode="off")
    store = TrainingStore(settings.database_path)
    store.sync_questions((question,))
    session_id = store.create_session(Mode.DAILY)
    attempt_id = store.record_answer(
        session_id=session_id,
        question_id=question.id,
        prompt_snapshot=question.prompt,
        family_snapshot=question.family,
        answer="saved answer",
        assistance=Assistance.NONE,
        hint_count=0,
        is_followup=False,
        is_cold_recall=False,
        is_transfer=False,
    )

    class StaticProvider:
        def __init__(self, name, model, score):
            self.name = name
            self.model = model
            self.score = score

        def evaluate(self, question, answer, mode):
            return Evaluation(
                outcome=Outcome.PASS,
                score=self.score,
                met=tuple(item.id for item in question.criteria),
                missing=(),
                feedback="calibration",
                evaluator=f"{self.name}:{self.model}:reasoning",
                evaluator_provider=self.name,
                evaluator_model=self.model,
                evaluation_mode="reasoning",
            )

    results = evaluate_for_calibration(
        store=store,
        attempt_id=attempt_id,
        question=question,
        answer="saved answer",
        mode=Mode.DAILY,
        providers=(
            StaticProvider("qwen_local", "local-qwen", 0.8),
            StaticProvider("openai", "gpt-5.6-sol", 0.9),
        ),
    )
    assert [result.score for result in results] == [0.8, 0.9]
    assert [row["provider"] for row in store.evaluation_runs(attempt_id)] == [
        "qwen_local",
        "openai",
    ]
    assert store.competency(question.competency)["attempts"] == 0


def test_qwen_environment_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("TRAINING_DB", str(tmp_path / "training.db"))
    monkeypatch.setenv("EVALUATOR_PROVIDER", "qwen_local")
    monkeypatch.setenv("QWEN_BASE_URL", "http://127.0.0.1:9999/v1/")
    monkeypatch.setenv("QWEN_MODEL", "custom-qwen")
    monkeypatch.setenv("QWEN_API_KEY", "placeholder")
    settings = Settings.from_env()
    assert settings.evaluator_provider == "qwen_local"
    assert settings.qwen_base_url == "http://127.0.0.1:9999/v1"
    assert settings.qwen_model == "custom-qwen"
    # Central migration: the project no longer reads provider credentials.
    assert settings.qwen_api_key == "local"
