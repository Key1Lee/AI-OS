from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.assessment import CANONICAL_COMPETENCIES
from app.models import AssistanceLevel, CompetencyState, SessionStatus


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL UNIQUE,
                    target_role TEXT NOT NULL,
                    module TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    scenario_title TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    current_question TEXT NOT NULL,
                    constraints_json TEXT NOT NULL DEFAULT '[]',
                    competencies_json TEXT NOT NULL,
                    turn_number INTEGER NOT NULL DEFAULT 1,
                    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    assistance_level TEXT NOT NULL,
                    hints_used INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    accumulated_seconds INTEGER NOT NULL DEFAULT 0,
                    active_since TEXT,
                    previous_response_id TEXT,
                    module_review_json TEXT,
                    next_recommended_assessment TEXT NOT NULL DEFAULT '',
                    last_error TEXT,
                    failure_streak INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    request_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT,
                    turn_id INTEGER
                );
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    request_id TEXT NOT NULL UNIQUE REFERENCES submissions(request_id),
                    turn_number INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    input_kind TEXT NOT NULL,
                    candidate_input TEXT NOT NULL,
                    interviewer_message TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    response_id TEXT,
                    model TEXT NOT NULL,
                    reasoning_effort TEXT NOT NULL,
                    usage_json TEXT NOT NULL DEFAULT '{}',
                    duration_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS competency_progress (
                    competency TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    demonstrated_level TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS weaknesses (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    competency TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    remediation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence_syncs (
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    module TEXT NOT NULL,
                    synced_at TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    PRIMARY KEY (session_id, module)
                );
                """
            )
            now = utc_now()
            connection.executemany(
                """
                INSERT OR IGNORE INTO competency_progress
                    (competency, state, updated_at)
                VALUES (?, ?, ?)
                """,
                [(item, CompetencyState.UNTESTED.value, now) for item in CANONICAL_COMPETENCIES],
            )

    def next_assessment_id(self) -> str:
        with self.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()
            number = int(row["count"]) + 1
            return f"A-{number:03d}"

    def create_session(self, values: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, assessment_id, target_role, module, scenario_id,
                    scenario_title, scenario, current_question, competencies_json,
                    difficulty, status, mode, assistance_level, started_at,
                    updated_at, active_since
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["id"], values["assessment_id"], values["target_role"],
                    values["module"], values["scenario_id"], values["scenario_title"],
                    values["scenario"], values["current_question"],
                    json.dumps(values["competencies"]), values["difficulty"],
                    SessionStatus.ACTIVE.value, "ASSESSMENT", AssistanceLevel.NONE.value,
                    values["started_at"], values["started_at"], values["started_at"],
                ),
            )
        return self.get_session(values["id"])

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(session_id)
        return dict(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def create_or_get_submission(
        self, request_id: str, session_id: str, kind: str, content: str
    ) -> tuple[dict[str, Any], bool]:
        now = utc_now()
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM submissions WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row is not None:
                existing = dict(row)
                if existing["session_id"] != session_id or existing["kind"] != kind or existing["content"] != content:
                    raise ValueError("request_id was already used for a different submission")
                return existing, False
            connection.execute(
                """
                INSERT INTO submissions
                    (request_id, session_id, kind, content, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (request_id, session_id, kind, content, now, now),
            )
        return self.get_submission(request_id), True

    def get_submission(self, request_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM submissions WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise KeyError(request_id)
        return dict(row)

    def mark_submission_processing(self, request_id: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE submissions SET status = 'PROCESSING', error = NULL, updated_at = ? WHERE request_id = ?",
                (utc_now(), request_id),
            )

    def mark_submission_failed(self, request_id: str, session_id: str, error: str) -> None:
        now = utc_now()
        safe_error = error[:2_000]
        with self.connection() as connection:
            connection.execute(
                "UPDATE submissions SET status = 'FAILED', error = ?, updated_at = ? WHERE request_id = ?",
                (safe_error, now, request_id),
            )
            connection.execute(
                "UPDATE sessions SET last_error = ?, updated_at = ? WHERE id = ?",
                (safe_error, now, session_id),
            )

    def recent_turns(self, session_id: str, limit: int = 12) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM (
                    SELECT * FROM turns WHERE session_id = ? ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (session_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def complete_turn(
        self,
        *,
        session_id: str,
        request_id: str,
        input_kind: str,
        candidate_input: str,
        previous_question: str,
        interviewer_message: str,
        decision_json: str,
        response_id: str | None,
        model: str,
        reasoning_effort: str,
        usage_json: str,
        duration_ms: int,
        session_updates: dict[str, Any],
    ) -> int:
        now = utc_now()
        with self.connection() as connection:
            session = connection.execute(
                "SELECT turn_number FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if session is None:
                raise KeyError(session_id)
            cursor = connection.execute(
                """
                INSERT INTO turns (
                    session_id, request_id, turn_number, question, input_kind,
                    candidate_input, interviewer_message, decision_json, response_id,
                    model, reasoning_effort, usage_json, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, request_id, session["turn_number"], previous_question,
                    input_kind, candidate_input, interviewer_message, decision_json,
                    response_id, model, reasoning_effort, usage_json, duration_ms, now,
                ),
            )
            turn_id = int(cursor.lastrowid)
            allowed = {
                "module", "current_question", "constraints_json", "turn_number",
                "difficulty", "status", "mode", "assistance_level", "hints_used",
                "previous_response_id", "module_review_json",
                "next_recommended_assessment", "last_error", "active_since",
                "accumulated_seconds", "failure_streak",
            }
            unexpected = set(session_updates) - allowed
            if unexpected:
                raise ValueError(f"Unsupported session update: {sorted(unexpected)}")
            assignments = [f"{key} = ?" for key in session_updates]
            values = list(session_updates.values())
            assignments.append("updated_at = ?")
            values.append(now)
            values.append(session_id)
            connection.execute(
                f"UPDATE sessions SET {', '.join(assignments)} WHERE id = ?", values
            )
            connection.execute(
                """
                UPDATE submissions
                SET status = 'COMPLETED', turn_id = ?, error = NULL, updated_at = ?
                WHERE request_id = ?
                """,
                (turn_id, now, request_id),
            )
        return turn_id

    def set_status(self, session_id: str, status: SessionStatus) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as connection:
            row = connection.execute(
                "SELECT status, active_since, accumulated_seconds FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise KeyError(session_id)
            accumulated = int(row["accumulated_seconds"])
            active_since = row["active_since"]
            if row["status"] == SessionStatus.ACTIVE.value and active_since:
                accumulated += max(0, int((datetime.now(UTC) - datetime.fromisoformat(active_since)).total_seconds()))
            new_active_since = now if status == SessionStatus.ACTIVE else None
            connection.execute(
                """
                UPDATE sessions SET status = ?, accumulated_seconds = ?,
                    active_since = ?, updated_at = ?, last_error = NULL
                WHERE id = ?
                """,
                (status.value, accumulated, new_active_since, now, session_id),
            )
        return self.get_session(session_id)

    def set_last_error(self, session_id: str, error: str | None) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE sessions SET last_error = ?, updated_at = ? WHERE id = ?",
                ((error[:2_000] if error else None), utc_now(), session_id),
            )

    def update_competency(
        self, competency: str, state: str, level: str, evidence: str
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE competency_progress
                SET state = ?, demonstrated_level = ?, evidence = ?, updated_at = ?
                WHERE competency = ?
                """,
                (state, level, evidence, utc_now(), competency),
            )

    def add_weakness(
        self,
        weakness_id: str,
        session_id: str,
        competency: str,
        classification: str,
        evidence: str,
        remediation: str,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO weaknesses (
                    id, session_id, competency, classification, evidence,
                    remediation, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """,
                (weakness_id, session_id, competency, classification, evidence, remediation, utc_now()),
            )

    def next_weakness_id(self) -> str:
        with self.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM weaknesses").fetchone()
        return f"W-{int(row['count']) + 1:03d}"

    def dashboard(self) -> dict[str, Any]:
        with self.connection() as connection:
            competencies = [dict(row) for row in connection.execute(
                "SELECT * FROM competency_progress ORDER BY rowid"
            ).fetchall()]
            weaknesses = [dict(row) for row in connection.execute(
                "SELECT * FROM weaknesses ORDER BY created_at DESC"
            ).fetchall()]
        sessions = self.list_sessions()
        return {"sessions": sessions, "competencies": competencies, "weaknesses": weaknesses}

    def sync_exists(self, session_id: str, module: str) -> bool:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM evidence_syncs WHERE session_id = ? AND module = ?",
                (session_id, module),
            ).fetchone()
        return row is not None

    def record_sync(self, session_id: str, module: str, artifact_path: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO evidence_syncs (session_id, module, synced_at, artifact_path)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, module, utc_now(), artifact_path),
            )
