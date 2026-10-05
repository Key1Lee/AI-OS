from training.config import Settings
from training.content import load_questions
from training.evaluation import evaluate_deterministically
from training.models import Assistance, Mode
from training.persistence import TrainingStore
from training.scheduling import next_review_at
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import gc
import json
from pathlib import Path
import subprocess
import sys
import pytest
from training.models import Criterion, Evaluation, Outcome, Question


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
    assert store.competency(question.competency)["independent_successes"] == 0
    assert store.competency(question.competency)["mastery"] == 0

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


def synthetic_question(family="base"):
    return Question(id=f"synthetic-{family}", competency="Synthetic reasoning", family=family,
                    difficulty=1, prompt="Explain retry correctness.",
                    criteria=(Criterion("idempotency", "Explain idempotency", ("idempotency",)),
                              Criterion("verification", "Explain verification", ("verification",))),
                    hints=(), followups={})


def coverage(question):
    return evaluate_deterministically(question, "Idempotency and verification are irrelevant; never use either.")


def reasoning(question, outcome=Outcome.PASS):
    return replace(coverage(question), outcome=outcome, evaluation_mode="reasoning",
                   evaluator_provider="mock-reasoning", evaluator_model="synthetic-model")


def record(store, question, evaluation, *, assistance=Assistance.NONE, cold=False,
           transfer=False, followup=False, mode=Mode.DAILY):
    store.sync_questions((question,))
    session = store.create_session(mode)
    attempt = store.record_answer(session_id=session, question_id=question.id,
                                 prompt_snapshot=question.prompt, family_snapshot=question.family,
                                 answer="Synthetic preserved answer", assistance=assistance,
                                 hint_count=int(assistance != Assistance.NONE), is_followup=followup,
                                 is_cold_recall=cold, is_transfer=transfer)
    store.record_evaluation(attempt_id=attempt, question=question, evaluation=evaluation,
                            assistance=assistance, mode=mode, is_followup=followup,
                            is_cold_recall=cold, is_transfer=transfer,
                            next_review_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
    return attempt


@pytest.mark.parametrize("outcome", [Outcome.PASS, Outcome.FAIL])
@pytest.mark.parametrize("assistance", [Assistance.NONE, Assistance.LIGHT])
@pytest.mark.parametrize("cold,transfer", [(False, False), (True, True)])
def test_coverage_cannot_change_any_assessed_effect_or_trust_caller_spacing(tmp_path, outcome, assistance, cold, transfer):
    store = TrainingStore(tmp_path / "synthetic.db")
    question = synthetic_question()
    record(store, question, reasoning(question, Outcome.FAIL))
    before = dict(store.competency(question.competency))
    attempt = record(store, question, replace(coverage(question), outcome=outcome),
                     assistance=assistance, cold=cold, transfer=transfer)
    row = dict(store.competency(question.competency))
    for field in ("mastery", "state", "independent_successes", "hinted_successes", "failures",
                  "cold_recall_successes", "transfer_successes", "consecutive_failures"):
        assert row[field] == before[field], field
    assert row["attempts"] == before["attempts"] + 1
    with store.connect() as connection:
        saved = connection.execute("SELECT * FROM attempts WHERE id=?", (attempt,)).fetchone()
        scheduled = connection.execute("SELECT * FROM review_schedule WHERE attempt_id=?", (attempt,)).fetchone()
    assert saved["outcome"] == outcome.value  # Raw diagnostic outcome survives.
    assert json.loads(saved["evaluation_json"])["assessment_outcome"] is None
    assert "unassessed_practice" in scheduled["reason"]
    assert datetime.fromisoformat(row["next_review_at"]) <= datetime.fromisoformat(saved["evaluated_at"]) + timedelta(days=1)
    assert len(store.open_weaknesses()) == 1  # No semantic weakness invented from missing words.


def test_lexical_families_do_not_satisfy_mastery_family_requirement(tmp_path):
    store = TrainingStore(tmp_path / "synthetic.db")
    base, other, lexical = synthetic_question("base"), synthetic_question("other"), synthetic_question("lexical")
    record(store, base, reasoning(base), cold=True, mode=Mode.COLD_RECALL)
    record(store, base, reasoning(base))
    record(store, other, reasoning(other), transfer=True)
    record(store, other, reasoning(other), transfer=True)
    record(store, lexical, coverage(lexical), cold=True, transfer=True)
    record(store, other, reasoning(other), transfer=True)
    row = store.competency(base.competency)
    assert row["mastery"] == 0.87
    assert row["independent_successes"] == 5
    assert row["state"] == "RELIABLE"  # Only two assessed families; coverage cannot supply the third.


def test_authoritative_failure_is_retained_even_when_lexical_result_claims_pass(tmp_path):
    store = TrainingStore(tmp_path / "synthetic.db")
    question = synthetic_question()
    evaluation = replace(coverage(question), deterministic_results={"checks": [
        {"name": "sql_expected_rows", "authoritative": True, "passed": False},
    ]})
    attempt = record(store, question, evaluation)
    row = store.competency(question.competency)
    assert row["failures"] == 1 and row["consecutive_failures"] == 1
    assert row["independent_successes"] == 0
    with store.connect() as connection:
        saved = connection.execute("SELECT outcome,evaluation_json FROM attempts WHERE id=?", (attempt,)).fetchone()
    assert saved["outcome"] == "fail"
    assert json.loads(saved["evaluation_json"])["diagnostic_outcome"] == "pass"


def legacy_profile(tmp_path, *, inflate=True):
    store = TrainingStore(tmp_path / "legacy-synthetic.db")
    question = synthetic_question()
    attempt = record(store, question, coverage(question))
    with store.transaction() as connection:
        raw = connection.execute("SELECT evaluation_json FROM attempts WHERE id=?", (attempt,)).fetchone()[0]
        metadata = json.loads(raw)
        for key in ("credit_policy", "assessment_eligible", "assessment_outcome", "eligibility_reason", "diagnostic_outcome", "practice_interval_days"):
            metadata.pop(key, None)
        connection.execute("UPDATE attempts SET evaluation_json=? WHERE id=?", (json.dumps(metadata), attempt))
        connection.execute("UPDATE evaluation_runs SET result_json=? WHERE attempt_id=?", (json.dumps(metadata), attempt))
        if inflate:
            tested = "2025-01-01T00:00:00+00:00"
            review = "2025-01-31T00:00:00+00:00"
            connection.execute("UPDATE attempts SET evaluated_at=? WHERE id=?", (tested, attempt))
            connection.execute("UPDATE competencies SET mastery=0.12,independent_successes=1,state='LEARNING',last_tested_at=?,next_review_at=? WHERE name=?", (tested, review, question.competency))
            connection.execute("UPDATE review_schedule SET scheduled_for=? WHERE attempt_id=?", (review, attempt))
    quiesce(store.path)
    return store, question, attempt


def quiesce(path):
    # Preview's documented precondition is stopped writers/a consistent copy.
    # Existing store setup/read helpers use SQLite contexts rather than closing
    # every connection, so release those test handles before the checkpoint.
    gc.collect()
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def dump(path):
    with closing(sqlite3.connect(path)) as connection:
        return "\n".join(connection.iterdump())


def raw_history(store):
    with closing(store.connect()) as connection:
        return {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in ("attempts", "evaluation_runs", "review_schedule", "sessions", "questions")}


def test_preview_is_noninitializing_and_apply_is_backed_up_atomic_and_idempotent(tmp_path, monkeypatch):
    store, question, _ = legacy_profile(tmp_path)
    assert store.legacy_credit_competencies() == {question.competency}
    before_dump, before_history = dump(store.path), raw_history(store)
    before_files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.iterdir()}
    monkeypatch.setattr(TrainingStore, "__init__", lambda *a, **k: pytest.fail("Preview/apply must not initialize a store"))
    preview = TrainingStore.preview_credit_rebuild(store.path)
    assert before_files == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.iterdir()}
    result = preview["changes"][question.competency]["after"]
    assert result["mastery"] == 0 and result["independent_successes"] == 0
    assert result["last_tested_at"] == "2025-01-01T00:00:00+00:00"
    assert result["next_review_at"] == "2025-01-02T00:00:00+00:00"
    original_projection = TrainingStore._credit_projection
    def locked_projection(cls, connection, path):
        if connection.in_transaction:
            with closing(sqlite3.connect(path, timeout=0.01)) as writer:
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    writer.execute("UPDATE competencies SET mastery=0.99")
        return original_projection(connection, path)
    monkeypatch.setattr(TrainingStore, "_credit_projection", classmethod(locked_projection))
    applied = TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"])
    assert applied["applied"] and dump(Path(applied["backup"])) == before_dump
    assert raw_history(store) == before_history
    assert store.legacy_credit_competencies() == set()
    with store.connect() as connection:
        receipt = connection.execute("SELECT * FROM session_events WHERE event_type='training_credit_rebuilt'").fetchone()
    assert receipt["session_id"] is not None
    assert json.loads(receipt["detail"])["changes"][question.competency]["before"]["next_review_at"] == "2025-01-31T00:00:00+00:00"
    after_dump = dump(store.path)
    second = TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"])
    assert second["already_current"] and not second["applied"]
    assert dump(store.path) == after_dump
    restored = tmp_path / "restored.db"
    with closing(sqlite3.connect(applied["backup"])) as source, closing(sqlite3.connect(restored)) as destination:
        source.backup(destination)
    assert dump(restored) == before_dump


def test_unchanged_legacy_aggregates_still_receive_one_reviewed_receipt(tmp_path):
    store, question, _ = legacy_profile(tmp_path, inflate=False)
    preview = TrainingStore.preview_credit_rebuild(store.path)
    assert preview["changes"] == {} and preview["needs_receipt"]
    applied = TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"])
    assert applied["applied"] and store.legacy_credit_competencies() == set()
    assert not TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"])["applied"]


def test_unknown_legacy_evidence_is_visible_and_gets_no_invented_credit(tmp_path):
    store, question, attempt = legacy_profile(tmp_path)
    with store.transaction() as connection:
        connection.execute("UPDATE attempts SET evaluation_json='{}' WHERE id=?", (attempt,))
    quiesce(store.path)
    preview = TrainingStore.preview_credit_rebuild(store.path)
    assert preview["unverified_attempts"][0]["attempt_id"] == attempt
    assert preview["changes"][question.competency]["after"]["independent_successes"] == 0


def test_apply_refuses_stale_preview_or_overwriting_backup(tmp_path):
    store, _, _ = legacy_profile(tmp_path)
    preview = TrainingStore.preview_credit_rebuild(store.path)
    backup = tmp_path / "existing.db"
    backup.write_bytes(b"preserve this existing file")
    before = dump(store.path)
    with pytest.raises(ValueError, match="new file"):
        TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"], backup_path=backup)
    assert backup.read_bytes() == b"preserve this existing file" and dump(store.path) == before
    with store.transaction() as connection:
        connection.execute("UPDATE competencies SET independent_successes=2")
    before = dump(store.path)
    with pytest.raises(ValueError, match="changed since"):
        TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"])
    assert dump(store.path) == before


def test_preview_refuses_nonexistent_newer_or_active_wal_profiles_without_writes(tmp_path):
    missing = tmp_path / "not-created" / "missing.db"
    with pytest.raises(FileNotFoundError):
        TrainingStore.preview_credit_rebuild(missing)
    assert not missing.parent.exists()
    unsupported = tmp_path / "newer.db"
    with closing(sqlite3.connect(unsupported)) as connection:
        connection.execute("PRAGMA user_version=99")
    original = unsupported.read_bytes()
    with pytest.raises(ValueError, match="schema 2"):
        TrainingStore.preview_credit_rebuild(unsupported)
    assert unsupported.read_bytes() == original
    store, _, _ = legacy_profile(tmp_path)
    with closing(sqlite3.connect(store.path)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE competencies SET mastery=0.9")
        with pytest.raises(ValueError, match="WAL"):
            TrainingStore.preview_credit_rebuild(store.path)
        writer.rollback()


def test_invalid_historical_time_blocks_apply_and_cli_defaults_to_readonly(tmp_path):
    store, _, attempt = legacy_profile(tmp_path)
    with store.transaction() as connection:
        connection.execute("UPDATE attempts SET evaluated_at=NULL WHERE id=?", (attempt,))
    quiesce(store.path)
    before = dump(store.path)
    preview = TrainingStore.preview_credit_rebuild(store.path)
    assert preview["blockers"]
    with pytest.raises(ValueError, match="Unreconstructable"):
        TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"])
    assert dump(store.path) == before
    script = Path(__file__).resolve().parents[2] / "scripts" / "rebuild_training_credit.py"
    command = [sys.executable, str(script), "--database", str(store.path)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["applied"] is False and dump(store.path) == before
    refused = subprocess.run(command + ["--apply"], capture_output=True, text=True)
    assert refused.returncode == 2 and "expected-digest" in refused.stderr
    assert dump(store.path) == before


def test_failure_after_derived_update_rolls_back_atomically_and_keeps_exact_backup(tmp_path):
    store, _, _ = legacy_profile(tmp_path)
    with store.transaction() as connection:
        connection.execute("""CREATE TRIGGER synthetic_receipt_failure BEFORE INSERT ON session_events
            WHEN NEW.event_type='training_credit_rebuilt'
            BEGIN SELECT RAISE(ABORT,'synthetic receipt failure'); END""")
    quiesce(store.path)
    preview = TrainingStore.preview_credit_rebuild(store.path)
    before = dump(store.path)
    backup = tmp_path / "rollback-backup.db"
    with pytest.raises(sqlite3.IntegrityError, match="synthetic receipt failure"):
        TrainingStore.apply_credit_rebuild(store.path, expected_digest=preview["source_digest"], backup_path=backup)
    assert dump(store.path) == before
    assert dump(backup) == before


def test_apply_byte_limit_includes_committed_wal_before_loading(tmp_path, monkeypatch):
    import training.persistence as persistence
    store, _, _ = legacy_profile(tmp_path)
    with closing(sqlite3.connect(store.path)) as writer:
        writer.execute("INSERT INTO session_events(session_id,event_type,detail,created_at) VALUES(1,'synthetic-wal','preserved','2025-01-01')")
        writer.commit()
        wal_size = Path(str(store.path) + "-wal").stat().st_size
        assert wal_size > 0
        limit = store.path.stat().st_size + wal_size - 1
        monkeypatch.setattr(persistence, "MAX_REBUILD_BYTES", limit)
        before = dump(store.path)
        with pytest.raises(ValueError, match="including WAL"):
            TrainingStore.apply_credit_rebuild(store.path, expected_digest="not-loaded")
        assert dump(store.path) == before
