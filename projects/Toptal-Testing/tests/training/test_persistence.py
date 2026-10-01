from training.config import Settings
from training.content import load_questions
from training.evaluation import evaluate_deterministically
from training.models import Assistance, Mode
from training.persistence import TrainingStore
from training.scheduling import next_review_at


def test_answer_is_durable_before_evaluation_and_followup_does_not_inflate_mastery(tmp_path):
    settings = Settings(database_path=tmp_path / "training.db")
    store = TrainingStore(settings.database_path)
    question = load_questions()[0]
    store.sync_questions((question,))
    session_id = store.create_session(Mode.DAILY)
    attempt_id = store.record_answer(
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
    assert store.unanswered_evaluations(session_id)[0]["id"] == attempt_id
    evaluation = evaluate_deterministically(question, store.unanswered_evaluations(session_id)[0]["answer"])
    review = next_review_at(
        outcome=evaluation.outcome,
        assistance=Assistance.NONE,
        mode=Mode.DAILY,
        is_transfer=False,
        consecutive_failures=0,
        settings=settings,
    )
    store.record_evaluation(
        attempt_id=attempt_id,
        question=question,
        evaluation=evaluation,
        assistance=Assistance.NONE,
        mode=Mode.DAILY,
        is_followup=False,
        is_cold_recall=False,
        is_transfer=False,
        next_review_at=review.isoformat(),
    )
    assert store.competency(question.competency)["attempts"] == 1

    followup_id = store.record_answer(
        session_id=session_id,
        question_id=question.id,
        prompt_snapshot="Follow-up",
        family_snapshot=question.family,
        answer="The list object is created at function definition time.",
        assistance=Assistance.NONE,
        hint_count=0,
        is_followup=True,
        is_cold_recall=False,
        is_transfer=False,
    )
    store.record_evaluation(
        attempt_id=followup_id,
        question=question,
        evaluation=evaluation,
        assistance=Assistance.NONE,
        mode=Mode.DAILY,
        is_followup=True,
        is_cold_recall=False,
        is_transfer=False,
        next_review_at=review.isoformat(),
    )
    assert store.competency(question.competency)["attempts"] == 1
    assert store.integrity_check() == "ok"


def test_schema_upgrade_creates_backup_and_evaluation_audit_table(tmp_path):
    database = tmp_path / "training.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 1")
    store = TrainingStore(database)
    with store.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "evaluation_runs" in tables
    assert list(tmp_path.glob("training.db.backup-*"))
import sqlite3
