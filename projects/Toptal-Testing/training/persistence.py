from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .mastery import MasteryEvidence, classify, score_delta, updated_score
from .models import Assistance, Evaluation, Mode, Outcome, Question


SCHEMA_VERSION = 2


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrainingStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        existed = self.path.exists() and self.path.stat().st_size > 0
        with self.connect() as connection:
            current = connection.execute("PRAGMA user_version").fetchone()[0]
        if current > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema {current} is newer than supported {SCHEMA_VERSION}"
            )
        if existed and 0 < current < SCHEMA_VERSION:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            shutil.copy2(self.path, self.path.with_suffix(f".db.backup-{stamp}"))
        if current == SCHEMA_VERSION:
            return
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS learner_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS competencies (
                    name TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'UNSEEN',
                    mastery REAL NOT NULL DEFAULT 0.0 CHECK (mastery BETWEEN 0 AND 1),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    independent_successes INTEGER NOT NULL DEFAULT 0,
                    hinted_successes INTEGER NOT NULL DEFAULT 0,
                    failures INTEGER NOT NULL DEFAULT 0,
                    cold_recall_successes INTEGER NOT NULL DEFAULT 0,
                    transfer_successes INTEGER NOT NULL DEFAULT 0,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    last_tested_at TEXT,
                    next_review_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    competency TEXT NOT NULL REFERENCES competencies(name),
                    family TEXT NOT NULL,
                    difficulty INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('active','paused','completed')),
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    summary_json TEXT
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id),
                    question_id TEXT NOT NULL REFERENCES questions(id),
                    prompt_snapshot TEXT NOT NULL,
                    family_snapshot TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    evaluation_json TEXT,
                    outcome TEXT,
                    assistance TEXT NOT NULL,
                    hint_count INTEGER NOT NULL DEFAULT 0,
                    is_followup INTEGER NOT NULL DEFAULT 0,
                    is_cold_recall INTEGER NOT NULL DEFAULT 0,
                    is_transfer INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL CHECK (status IN ('answered','evaluated')),
                    created_at TEXT NOT NULL,
                    evaluated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS weaknesses (
                    id TEXT PRIMARY KEY,
                    competency TEXT NOT NULL REFERENCES competencies(name),
                    context TEXT NOT NULL,
                    surface_mistake TEXT NOT NULL,
                    misconception TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    assistance TEXT NOT NULL,
                    corrective_principle TEXT NOT NULL,
                    next_review_at TEXT NOT NULL,
                    transfer_requirement TEXT NOT NULL,
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competency TEXT NOT NULL REFERENCES competencies(name),
                    scheduled_for TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    attempt_id INTEGER REFERENCES attempts(id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id),
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
                    assessment_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    evaluation_mode TEXT NOT NULL,
                    rubric_version TEXT NOT NULL,
                    deterministic_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    fallback_reason TEXT,
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
                CREATE INDEX IF NOT EXISTS idx_attempts_question ON attempts(question_id);
                CREATE INDEX IF NOT EXISTS idx_reviews_due ON review_schedule(status, scheduled_for);
                CREATE INDEX IF NOT EXISTS idx_weakness_status ON weaknesses(status, next_review_at);
                CREATE INDEX IF NOT EXISTS idx_evaluation_runs_attempt ON evaluation_runs(attempt_id);
                """
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            now = iso_now()
            connection.execute(
                "INSERT OR IGNORE INTO learner_profile(id, created_at, last_seen_at) VALUES(1, ?, ?)",
                (now, now),
            )

    def integrity_check(self) -> str:
        with self.connect() as connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0])

    def sync_questions(self, questions: tuple[Question, ...]) -> None:
        now = iso_now()
        with self.transaction() as connection:
            connection.execute("UPDATE learner_profile SET last_seen_at = ? WHERE id = 1", (now,))
            for question in questions:
                connection.execute(
                    "INSERT OR IGNORE INTO competencies(name, updated_at) VALUES(?, ?)",
                    (question.competency, now),
                )
                connection.execute(
                    """
                    INSERT INTO questions(id, competency, family, difficulty, prompt, source, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      competency=excluded.competency, family=excluded.family,
                      difficulty=excluded.difficulty, prompt=excluded.prompt,
                      source=excluded.source, updated_at=excluded.updated_at
                    """,
                    (
                        question.id,
                        question.competency,
                        question.family,
                        question.difficulty,
                        question.prompt,
                        question.source,
                        now,
                    ),
                )

    def competency_rows(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute("SELECT * FROM competencies ORDER BY name"))

    def competency(self, name: str) -> sqlite3.Row:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM competencies WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise KeyError(name)
        return row

    def question_attempt_count(self, question_id: str) -> int:
        with self.connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM attempts WHERE question_id = ? AND status = 'evaluated'",
                    (question_id,),
                ).fetchone()[0]
            )

    def last_question_id(self) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT question_id FROM attempts WHERE status = 'evaluated' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return str(row[0]) if row else None

    def last_competency(self) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT q.competency FROM attempts a JOIN questions q ON q.id = a.question_id
                WHERE a.status = 'evaluated' AND a.is_followup = 0 ORDER BY a.id DESC LIMIT 1
                """
            ).fetchone()
        return str(row[0]) if row else None

    def competency_family_attempted(self, competency: str, family: str) -> bool:
        with self.connect() as connection:
            count = connection.execute(
                """
                SELECT COUNT(*) FROM attempts a JOIN questions q ON q.id = a.question_id
                WHERE q.competency = ? AND a.family_snapshot = ? AND a.status = 'evaluated'
                  AND a.is_followup = 0
                """,
                (competency, family),
            ).fetchone()[0]
        return bool(count)

    def active_session(self) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM sessions WHERE status IN ('active','paused') ORDER BY id DESC LIMIT 1"
            ).fetchone()

    def create_session(self, mode: Mode) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO sessions(mode, status, started_at) VALUES(?, 'active', ?)",
                (mode.value, iso_now()),
            )
            return int(cursor.lastrowid)

    def set_session_status(self, session_id: int, status: str, summary: dict | None = None) -> None:
        if status not in {"active", "paused", "completed"}:
            raise ValueError(status)
        ended_at = iso_now() if status == "completed" else None
        with self.transaction() as connection:
            connection.execute(
                "UPDATE sessions SET status = ?, ended_at = ?, summary_json = ? WHERE id = ?",
                (status, ended_at, json.dumps(summary) if summary is not None else None, session_id),
            )

    def resume_session(self, session_id: int) -> None:
        with self.transaction() as connection:
            connection.execute("UPDATE sessions SET status = 'active' WHERE id = ?", (session_id,))

    def record_event(self, session_id: int, event_type: str, detail: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO session_events(session_id, event_type, detail, created_at) VALUES(?, ?, ?, ?)",
                (session_id, event_type, detail, iso_now()),
            )

    def record_answer(
        self,
        *,
        session_id: int,
        question_id: str,
        prompt_snapshot: str,
        family_snapshot: str,
        answer: str,
        assistance: Assistance,
        hint_count: int,
        is_followup: bool,
        is_cold_recall: bool,
        is_transfer: bool,
    ) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO attempts(
                    session_id, question_id, prompt_snapshot, family_snapshot, answer, assistance, hint_count,
                    is_followup, is_cold_recall, is_transfer, status, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'answered', ?)
                """,
                (
                    session_id,
                    question_id,
                    prompt_snapshot,
                    family_snapshot,
                    answer,
                    assistance.value,
                    hint_count,
                    int(is_followup),
                    int(is_cold_recall),
                    int(is_transfer),
                    iso_now(),
                ),
            )
            return int(cursor.lastrowid)

    def record_evaluation(
        self,
        *,
        attempt_id: int,
        question: Question,
        evaluation: Evaluation,
        assistance: Assistance,
        mode: Mode,
        is_followup: bool,
        is_cold_recall: bool,
        is_transfer: bool,
        next_review_at: str,
    ) -> None:
        now = iso_now()
        payload = self._evaluation_payload(evaluation)
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE attempts SET evaluation_json = ?, outcome = ?, status = 'evaluated', evaluated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(payload),
                    evaluation.outcome.value,
                    now,
                    attempt_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO evaluation_runs(
                  attempt_id, assessment_id, provider, model, evaluation_mode,
                  rubric_version, deterministic_json, result_json, fallback_reason,
                  is_primary, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    attempt_id,
                    question.id,
                    evaluation.evaluator_provider,
                    evaluation.evaluator_model,
                    evaluation.evaluation_mode,
                    evaluation.rubric_version,
                    json.dumps(evaluation.deterministic_results),
                    json.dumps(payload),
                    evaluation.fallback_reason,
                    now,
                ),
            )
            # A prompted follow-up is diagnostic evidence, not a fresh independent
            # mastery attempt. Persist it, but do not inflate mastery or spacing.
            if is_followup:
                return
            row = connection.execute(
                "SELECT * FROM competencies WHERE name = ?", (question.competency,)
            ).fetchone()
            assert row is not None
            passed = evaluation.outcome == Outcome.PASS
            independent = passed and assistance == Assistance.NONE
            attempts = int(row["attempts"]) + 1
            independent_successes = int(row["independent_successes"]) + int(independent)
            hinted_successes = int(row["hinted_successes"]) + int(passed and not independent)
            failures = int(row["failures"]) + int(evaluation.outcome == Outcome.FAIL)
            consecutive_failures = (
                int(row["consecutive_failures"]) + 1
                if evaluation.outcome == Outcome.FAIL
                else 0
            )
            cold_successes = int(row["cold_recall_successes"]) + int(
                independent and is_cold_recall
            )
            transfer_successes = int(row["transfer_successes"]) + int(
                independent and is_transfer
            )
            family_count = int(
                connection.execute(
                    """
                    SELECT COUNT(DISTINCT a.family_snapshot)
                    FROM attempts a JOIN questions q ON q.id = a.question_id
                    WHERE q.competency = ? AND a.outcome = 'pass' AND a.assistance = 'none'
                      AND a.is_followup = 0
                    """,
                    (question.competency,),
                ).fetchone()[0]
            )
            mastery = updated_score(
                float(row["mastery"]),
                score_delta(evaluation.outcome, assistance, mode, is_transfer),
            )
            evidence = MasteryEvidence(
                attempts=attempts,
                independent_successes=independent_successes,
                hinted_successes=hinted_successes,
                failures=failures,
                cold_recall_successes=cold_successes,
                transfer_successes=transfer_successes,
                distinct_families=family_count,
                consecutive_failures=consecutive_failures,
            )
            state = classify(mastery, evidence).value
            connection.execute(
                """
                UPDATE competencies SET state=?, mastery=?, attempts=?, independent_successes=?,
                  hinted_successes=?, failures=?, cold_recall_successes=?, transfer_successes=?,
                  consecutive_failures=?, last_tested_at=?, next_review_at=?, updated_at=?
                WHERE name=?
                """,
                (
                    state,
                    mastery,
                    attempts,
                    independent_successes,
                    hinted_successes,
                    failures,
                    cold_successes,
                    transfer_successes,
                    consecutive_failures,
                    now,
                    next_review_at,
                    now,
                    question.competency,
                ),
            )
            reason = f"{evaluation.outcome.value}:{assistance.value}:{mode.value}"
            connection.execute(
                """
                INSERT INTO review_schedule(competency, scheduled_for, reason, attempt_id, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (question.competency, next_review_at, reason, attempt_id, now),
            )
            if evaluation.outcome != Outcome.PASS:
                missing = ",".join(evaluation.missing) or "incomplete-reasoning"
                weakness_id = hashlib.sha256(
                    f"{question.competency}|{missing}".encode("utf-8")
                ).hexdigest()[:12]
                connection.execute(
                    """
                    INSERT INTO weaknesses(
                      id, competency, context, surface_mistake, misconception, severity,
                      assistance, corrective_principle, next_review_at, transfer_requirement,
                      created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      occurrences=occurrences+1, severity=excluded.severity,
                      assistance=excluded.assistance, next_review_at=excluded.next_review_at,
                      status='open', updated_at=excluded.updated_at
                    """,
                    (
                        weakness_id,
                        question.competency,
                        question.family,
                        evaluation.feedback,
                        evaluation.misconception or "Incomplete explicit reasoning",
                        "high" if evaluation.outcome == Outcome.FAIL else "medium",
                        assistance.value,
                        "Address every rubric dimension explicitly and validate it with evidence.",
                        next_review_at,
                        f"Pass an independent question in a different {question.competency} context.",
                        now,
                        now,
                    ),
                )

    def session_attempts(self, session_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM attempts WHERE session_id = ? ORDER BY id", (session_id,)
                )
            )

    def unanswered_evaluations(self, session_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM attempts WHERE session_id = ? AND status = 'answered' ORDER BY id",
                    (session_id,),
                )
            )

    @staticmethod
    def _evaluation_payload(evaluation: Evaluation) -> dict:
        return {
            "score": evaluation.score,
            "met": evaluation.met,
            "missing": evaluation.missing,
            "feedback": evaluation.feedback,
            "misconception": evaluation.misconception,
            "evaluator": evaluation.evaluator,
            "evaluator_provider": evaluation.evaluator_provider,
            "evaluator_model": evaluation.evaluator_model,
            "evaluation_mode": evaluation.evaluation_mode,
            "evaluation_confidence": evaluation.evaluation_confidence,
            "rubric_version": evaluation.rubric_version,
            "dimension_scores": evaluation.dimension_scores,
            "strengths": evaluation.strengths,
            "weaknesses": evaluation.weaknesses,
            "missed_concepts": evaluation.missed_concepts,
            "critical_errors": evaluation.critical_errors,
            "unsupported_assumptions": evaluation.unsupported_assumptions,
            "follow_up_questions": evaluation.follow_up_questions,
            "evidence": evaluation.evidence,
            "deterministic_results": evaluation.deterministic_results,
            "fallback_reason": evaluation.fallback_reason,
            "raw": evaluation.raw,
        }

    def record_calibration_evaluation(
        self,
        *,
        attempt_id: int,
        assessment_id: str,
        evaluation: Evaluation,
    ) -> int:
        payload = self._evaluation_payload(evaluation)
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO evaluation_runs(
                  attempt_id, assessment_id, provider, model, evaluation_mode,
                  rubric_version, deterministic_json, result_json, fallback_reason,
                  is_primary, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    attempt_id,
                    assessment_id,
                    evaluation.evaluator_provider,
                    evaluation.evaluator_model,
                    evaluation.evaluation_mode,
                    evaluation.rubric_version,
                    json.dumps(evaluation.deterministic_results),
                    json.dumps(payload),
                    evaluation.fallback_reason,
                    iso_now(),
                ),
            )
            return int(cursor.lastrowid)

    def evaluation_runs(self, attempt_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM evaluation_runs WHERE attempt_id = ? ORDER BY id",
                    (attempt_id,),
                )
            )

    def open_weaknesses(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM weaknesses WHERE status = 'open' ORDER BY severity DESC, next_review_at"
                )
            )
