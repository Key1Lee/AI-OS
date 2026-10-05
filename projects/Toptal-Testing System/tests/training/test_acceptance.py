from training.application import TrainingApplication
from training.config import Settings
from training.models import Assistance, Evaluation, Mode, Outcome
from training.llm import LLMUnavailable
from training.persistence import TrainingStore
from datetime import datetime, timedelta
import json

from .helpers import ScriptedIO


def config(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "training.db",
        llm_mode="off",
        session_questions=1,
    )


def test_two_launch_daily_flow_persists_and_adapts(tmp_path):
    first_io = ScriptedIO(
        [
            "",
            "The mutable default is created once and shared across calls. Use None and if tags is None set tags = []. A test makes two calls and expects independent lists.",
            "/submit",
        ]
    )
    assert TrainingApplication(config(tmp_path), first_io).run() == 0
    assert "SESSION COMPLETE" in first_io.transcript
    assert "Python semantics" in first_io.transcript

    second_io = ScriptedIO(
        [
            "",
            "Use a versioned schema contract and validate it. Verify an HMAC signature and timestamp for authentication. Use an idempotency event id for deduplication and sequence checks for out-of-order delivery.",
            "/submit",
        ]
    )
    assert TrainingApplication(config(tmp_path), second_io).run() == 0
    # A-03: persisted exposure is attempted practice, not an assessed success.
    assert "Progress: 1/14 competencies attempted" in second_io.transcript
    assert "API and integration design" in second_io.transcript
    store = TrainingStore(config(tmp_path).database_path)
    assert store.competency("Python semantics")["attempts"] == 1
    assert store.competency("API and integration design")["attempts"] == 1
    assert store.competency("Python semantics")["independent_successes"] == 0
    assert store.competency("Python semantics")["mastery"] == 0
    assert "unassessed/diagnostic 1" in first_io.transcript
    assert store.integrity_check() == "ok"


def test_assessment_denies_and_records_hint_request(tmp_path):
    io = ScriptedIO(
        [
            "4",
            "/hint",
            "The mutable default is created once and shared across calls. Use None; test two calls for independent results.",
            "/submit",
        ]
    )
    assert TrainingApplication(config(tmp_path), io).run() == 0
    assert "Hints are disabled" in io.transcript
    store = TrainingStore(config(tmp_path).database_path)
    with store.connect() as connection:
        events = [row[0] for row in connection.execute("SELECT event_type FROM session_events")]
    assert events == ["hint_requested", "hint_denied"]


class FakeProvider:
    name = "mock-openai"

    def evaluate(self, question, answer, mode):
        return Evaluation(
            outcome=Outcome.PASS,
            score=0.9,
            met=tuple(item.id for item in question.criteria),
            missing=(),
            feedback="Structured model evaluation.",
            evaluator="mock-openai:gpt-5.6-sol:medium",
            evaluator_provider="mock-openai",
            evaluator_model="synthetic-model",
            evaluation_mode="reasoning",
        )


def test_optional_llm_path_is_dependency_injected(tmp_path):
    io = ScriptedIO(["", "A reasoned answer", "/submit"])
    app = TrainingApplication(config(tmp_path), io, provider=FakeProvider())
    assert app.run() == 0
    assert "Evaluator: mock-openai" in io.transcript
    with app.store.connect() as connection:
        payload = connection.execute("SELECT evaluation_json FROM attempts").fetchone()[0]
    assert "mock-openai:gpt-5.6-sol:medium" in payload
    assert app.store.competency("Python semantics")["independent_successes"] == 1


class FailingProvider:
    name = "failing-provider"

    def evaluate(self, question, answer, mode):
        raise LLMUnavailable("simulated outage")


def test_required_llm_failure_pauses_without_losing_answer(tmp_path):
    settings = Settings(
        database_path=tmp_path / "training.db",
        llm_mode="required",
        session_questions=1,
    )
    io = ScriptedIO(["", "A durable answer", "/submit"])
    assert TrainingApplication(settings, io, provider=FailingProvider()).run() == 3
    with TrainingStore(settings.database_path).connect() as connection:
        attempt = connection.execute("SELECT status, answer FROM attempts").fetchone()
        session = connection.execute("SELECT status FROM sessions").fetchone()
    assert tuple(attempt) == ("answered", "A durable answer")
    assert session["status"] == "paused"


def test_optional_injected_evaluator_outage_retains_only_practice_evidence(tmp_path):
    settings = Settings(database_path=tmp_path / "training.db", llm_mode="auto", session_questions=1)
    io = ScriptedIO(["", "The mutable default is created once and shared across calls. Use None; test two calls for independent results.", "/submit"])
    app = TrainingApplication(settings, io, provider=FailingProvider())
    assert app.run() == 0
    with app.store.connect() as connection:
        attempt = connection.execute("SELECT * FROM attempts WHERE id=1").fetchone()
        summary = json.loads(connection.execute("SELECT summary_json FROM sessions WHERE id=1").fetchone()[0])
    payload = json.loads(attempt["evaluation_json"])
    assert payload["evaluation_mode"] == "lexical_conservative"
    assert payload["evaluator_provider"] == "offline_fallback"
    assert payload["fallback_reason"] == "simulated outage"
    assert payload["assessment_outcome"] is None
    row = app.store.competency("Python semantics")
    assert row["independent_successes"] == 0 and row["mastery"] == 0
    assert datetime.fromisoformat(row["next_review_at"]) <= datetime.fromisoformat(attempt["evaluated_at"]) + timedelta(days=1)
    assert summary["assessed"] == 0 and summary["diagnostic"] == 1 and summary["pass"] == 0
    assert "unassessed/diagnostic 1" in io.transcript


def test_interrupted_answer_is_evaluated_on_resume(tmp_path):
    settings = config(tmp_path)
    app = TrainingApplication(settings, ScriptedIO([]))
    question = app.questions[0]
    session_id = app.store.create_session(Mode.DAILY)
    app.store.record_answer(
        session_id=session_id,
        question_id=question.id,
        prompt_snapshot=question.prompt,
        family_snapshot=question.family,
        answer="mutable default created once shared across calls; use None; test two calls independent",
        assistance=Assistance.NONE,
        hint_count=0,
        is_followup=False,
        is_cold_recall=False,
        is_transfer=False,
    )
    resumed_io = ScriptedIO([""])
    assert TrainingApplication(settings, resumed_io).run() == 0
    assert "Recovering 1 saved answer" in resumed_io.transcript
    assert "SESSION COMPLETE" in resumed_io.transcript
    assert TrainingStore(settings.database_path).competency(question.competency)["attempts"] == 1
    assert TrainingStore(settings.database_path).competency(question.competency)["independent_successes"] == 0
    assert "unassessed/diagnostic 1" in resumed_io.transcript
    with app.store.connect() as connection:
        attempt = connection.execute("SELECT evaluated_at FROM attempts WHERE id=1").fetchone()
        summary = json.loads(connection.execute("SELECT summary_json FROM sessions WHERE id=?", (session_id,)).fetchone()[0])
    review = app.store.competency(question.competency)["next_review_at"]
    assert datetime.fromisoformat(review) <= datetime.fromisoformat(attempt["evaluated_at"]) + timedelta(days=1)
    assert summary["assessed"] == 0 and summary["diagnostic"] == 1 and summary["pass"] == 0
