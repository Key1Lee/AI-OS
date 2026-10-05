from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .config import Settings
from .mastery import (
    CREDIT_POLICY_VERSION, MasteryEvidence, assessment_eligibility,
    assessment_outcome, classify, score_delta, updated_score,
)
from .models import Assistance, Evaluation, Mode, Outcome, Question
from .scheduling import next_review_at as review_deadline


SCHEMA_VERSION = 2
MAX_REBUILD_ROWS = 10_000
MAX_REBUILD_BYTES = 64 * 1024 * 1024
CREDIT_FIELDS = (
    "state", "mastery", "attempts", "independent_successes", "hinted_successes",
    "failures", "cold_recall_successes", "transfer_successes", "consecutive_failures",
    "last_tested_at", "next_review_at",
)


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
        settings: Settings | None = None,
    ) -> None:
        now = iso_now()
        settings = settings or Settings(database_path=self.path)
        assessed = assessment_outcome(evaluation, evaluation.outcome)
        eligibility = assessment_eligibility(evaluation)
        payload = self._evaluation_payload(evaluation)
        payload["practice_interval_days"] = settings.failure_interval_days
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE attempts SET evaluation_json = ?, outcome = ?, status = 'evaluated', evaluated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(payload),
                    Outcome.FAIL.value if eligibility.authoritative_failure else evaluation.outcome.value,
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
            assessed_attempts, families = self._assessed_history(connection, question.competency)
            deadline = review_deadline(
                outcome=evaluation.outcome, evaluation=evaluation, assistance=assistance,
                mode=mode, is_transfer=is_transfer,
                consecutive_failures=int(row["consecutive_failures"]) + int(assessed == Outcome.FAIL),
                settings=settings, now=self._timestamp(now),
            )
            # Enforce the policy at the owning store too: direct callers cannot
            # turn practice into a successful assessment by supplying 30 days.
            review = min(self._timestamp(next_review_at), deadline).isoformat()
            updated = self._advance_credit(
                dict(row), metadata=payload, outcome=evaluation.outcome,
                assistance=assistance, mode=mode, is_cold_recall=is_cold_recall,
                is_transfer=is_transfer, assessed_attempts=assessed_attempts,
                families=len(families), tested_at=now, review_at=review,
            )
            connection.execute(
                """
                UPDATE competencies SET state=?, mastery=?, attempts=?, independent_successes=?,
                  hinted_successes=?, failures=?, cold_recall_successes=?, transfer_successes=?,
                  consecutive_failures=?, last_tested_at=?, next_review_at=?, updated_at=?
                WHERE name=?
                """,
                (
                    *(updated[field] for field in CREDIT_FIELDS),
                    now,
                    question.competency,
                ),
            )
            reason = f"{assessed.value if assessed else 'unassessed_practice'}:{assistance.value}:{mode.value}"
            connection.execute(
                """
                INSERT INTO review_schedule(competency, scheduled_for, reason, attempt_id, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (question.competency, review, reason, attempt_id, now),
            )
            if assessed is not None and assessed != Outcome.PASS:
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
                        "high" if assessed == Outcome.FAIL else "medium",
                        assistance.value,
                        "Address every rubric dimension explicitly and validate it with evidence.",
                        review,
                        f"Pass an independent question in a different {question.competency} context.",
                        now,
                        now,
                    ),
                )

    @staticmethod
    def _timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("Credit evidence timestamps must include a timezone")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _metadata(value: str | None) -> dict:
        try:
            parsed = json.loads(value or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @classmethod
    def _assessed_history(cls, connection, competency: str) -> tuple[int, set[str]]:
        assessed_attempts, families = 0, set()
        for attempt in connection.execute(
            """SELECT a.* FROM attempts a JOIN questions q ON q.id = a.question_id
               WHERE q.competency = ? AND a.status = 'evaluated' AND a.is_followup = 0""",
            (competency,),
        ):
            outcome = assessment_outcome(cls._metadata(attempt["evaluation_json"]), attempt["outcome"])
            if outcome is not None:
                assessed_attempts += 1
            if outcome == Outcome.PASS and attempt["assistance"] == Assistance.NONE.value:
                families.add(attempt["family_snapshot"])
        return assessed_attempts, families

    @staticmethod
    def _advance_credit(
        row: dict, *, metadata: dict, outcome: Outcome | str,
        assistance: Assistance, mode: Mode, is_cold_recall: bool,
        is_transfer: bool, assessed_attempts: int, families: int,
        tested_at: str, review_at: str,
    ) -> dict:
        updated = dict(row)
        updated["attempts"] += 1  # Keep exposure/durability independent from assessed credit.
        updated["last_tested_at"], updated["next_review_at"] = tested_at, review_at
        assessed = assessment_outcome(metadata, outcome)
        if assessed is None:
            return updated
        passed = assessed == Outcome.PASS
        independent = passed and assistance == Assistance.NONE
        updated["independent_successes"] += int(independent)
        updated["hinted_successes"] += int(passed and not independent)
        updated["failures"] += int(assessed == Outcome.FAIL)
        updated["consecutive_failures"] = updated["consecutive_failures"] + 1 if assessed == Outcome.FAIL else 0
        updated["cold_recall_successes"] += int(independent and is_cold_recall)
        updated["transfer_successes"] += int(independent and is_transfer)
        updated["mastery"] = updated_score(updated["mastery"], score_delta(assessed, assistance, mode, is_transfer))
        updated["state"] = classify(updated["mastery"], MasteryEvidence(
            attempts=assessed_attempts,
            independent_successes=updated["independent_successes"],
            hinted_successes=updated["hinted_successes"], failures=updated["failures"],
            cold_recall_successes=updated["cold_recall_successes"],
            transfer_successes=updated["transfer_successes"], distinct_families=families,
            consecutive_failures=updated["consecutive_failures"],
        )).value
        return updated

    def legacy_credit_competencies(self) -> set[str]:
        """A code patch does not claim to have repaired pre-policy aggregates."""
        with closing(self.connect()) as connection:
            corrected_through = self._corrected_through(connection.execute(
                "SELECT detail FROM session_events WHERE event_type = 'training_credit_rebuilt' ORDER BY id DESC"
            ))
            return {
                row["competency"] for row in connection.execute(
                    """SELECT q.competency, a.evaluation_json FROM attempts a
                       JOIN questions q ON q.id = a.question_id
                       WHERE a.status = 'evaluated' AND a.is_followup = 0 AND a.id > ?""",
                    (corrected_through,),
                ) if self._metadata(row["evaluation_json"]).get("credit_policy") != CREDIT_POLICY_VERSION
            }

    @classmethod
    def _corrected_through(cls, events) -> int:
        for event in events:
            receipt = cls._metadata(event["detail"])
            through = receipt.get("through_attempt_id")
            if receipt.get("policy") == CREDIT_POLICY_VERSION and isinstance(through, int) and through >= 0:
                return through
        return 0

    @staticmethod
    def _open_credit_database(path: Path, *, readonly: bool):
        path = Path(path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError("Select an existing training database file")
        if path.stat().st_size > MAX_REBUILD_BYTES:
            raise ValueError("Credit rebuild is limited to 64 MiB profiles")
        if readonly and Path(str(path) + "-wal").exists():
            # Immutable read-only access avoids even SQLite creating WAL/SHM
            # side files. It must not ignore uncheckpointed committed evidence.
            raise ValueError("Preview requires a quiescent/copied profile without a WAL file; stop writers or use a consistent backup")
        suffix = "?mode=ro&immutable=1" if readonly else "?mode=rw"
        connection = sqlite3.connect(path.as_uri() + suffix, uri=True, isolation_level=None, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise ValueError("Credit rebuild requires existing training schema 2; no initialization or migration is performed")
        except Exception:
            connection.close()
            raise
        return path, connection

    @classmethod
    def _credit_projection(cls, connection, path: Path) -> dict:
        profile_size = path.stat().st_size
        wal = Path(str(path) + "-wal")
        if wal.exists():
            profile_size += wal.stat().st_size
        if profile_size > MAX_REBUILD_BYTES:
            raise ValueError("Credit rebuild is limited to 64 MiB including WAL evidence")
        tables = {}
        for table in ("competencies", "questions", "sessions", "attempts", "evaluation_runs", "review_schedule", "session_events"):
            rows = connection.execute(f"SELECT * FROM {table} ORDER BY rowid LIMIT ?", (MAX_REBUILD_ROWS + 1,)).fetchall()
            if len(rows) > MAX_REBUILD_ROWS:
                raise ValueError(f"Credit rebuild is limited to {MAX_REBUILD_ROWS} rows per evidence table")
            tables[table] = [dict(row) for row in rows]
        encoded = json.dumps(tables, sort_keys=True, separators=(",", ":")).encode()
        if len(encoded) > MAX_REBUILD_BYTES:
            raise ValueError("Credit rebuild evidence is limited to 64 MiB")
        digest = hashlib.sha256(encoded).hexdigest()
        before = {row["name"]: {field: row[field] for field in CREDIT_FIELDS} for row in tables["competencies"]}
        after = {name: {
            "state": "UNSEEN", "mastery": 0.0, "attempts": 0,
            "independent_successes": 0, "hinted_successes": 0, "failures": 0,
            "cold_recall_successes": 0, "transfer_successes": 0, "consecutive_failures": 0,
            "last_tested_at": None, "next_review_at": None,
        } for name in before}
        questions = {row["id"]: row["competency"] for row in tables["questions"]}
        modes = {row["id"]: row["mode"] for row in tables["sessions"]}
        reviews = {row["attempt_id"]: row["scheduled_for"] for row in tables["review_schedule"]}
        families, assessed_counts = {name: set() for name in before}, {name: 0 for name in before}
        issues, blockers, ordered = [], [], []
        for attempt in tables["attempts"]:
            if attempt["status"] != "evaluated" or attempt["is_followup"]:
                continue
            try:
                tested = cls._timestamp(attempt["evaluated_at"])
                competency = questions[attempt["question_id"]]
                assistance, mode = Assistance(attempt["assistance"]), Mode(modes[attempt["session_id"]])
                if competency not in after:
                    raise ValueError("missing competency")
            except (KeyError, TypeError, ValueError) as exc:
                blockers.append({"attempt_id": attempt["id"], "reason": f"Cannot reconstruct identity/time/mode: {exc}"})
                continue
            ordered.append((tested, attempt["id"], attempt, competency, assistance, mode))
        for tested, _, attempt, name, assistance, mode in sorted(ordered, key=lambda item: item[:2]):
            metadata = cls._metadata(attempt["evaluation_json"])
            eligibility = assessment_eligibility(metadata)
            outcome = assessment_outcome(metadata, attempt["outcome"])
            if outcome is not None:
                assessed_counts[name] += 1
            elif eligibility.reason != "lexical_coverage":
                issues.append({"attempt_id": attempt["id"], "reason": eligibility.reason, "treatment": "unassessed practice; no invented credit"})
            if outcome == Outcome.PASS and assistance == Assistance.NONE:
                families[name].add(attempt["family_snapshot"])
            try:
                settings = Settings(database_path=path, failure_interval_days=float(metadata.get("practice_interval_days", 1.0)))
                if not math.isfinite(settings.failure_interval_days) or settings.failure_interval_days <= 0:
                    raise ValueError("invalid saved practice interval")
                deadline = review_deadline(
                    outcome=attempt["outcome"], evaluation=metadata, assistance=assistance,
                    mode=mode, is_transfer=bool(attempt["is_transfer"]),
                    consecutive_failures=after[name]["consecutive_failures"] + int(outcome == Outcome.FAIL),
                    settings=settings, now=tested,
                )
                saved_review = cls._timestamp(reviews[attempt["id"]]) if attempt["id"] in reviews else deadline
                # Preserve the recorded assessed interval; correct only the
                # unsupported practice success interval. Never re-date to today.
                review = saved_review if outcome is not None else min(saved_review, deadline)
            except (TypeError, ValueError) as exc:
                blockers.append({"attempt_id": attempt["id"], "reason": f"Cannot reconstruct review: {exc}"})
                continue
            after[name] = cls._advance_credit(
                after[name], metadata=metadata, outcome=attempt["outcome"],
                assistance=assistance, mode=mode, is_cold_recall=bool(attempt["is_cold_recall"]),
                is_transfer=bool(attempt["is_transfer"]), assessed_attempts=assessed_counts[name],
                families=len(families[name]), tested_at=attempt["evaluated_at"], review_at=review.isoformat(),
            )
        changes = {name: {"before": before[name], "after": after[name]} for name in before if before[name] != after[name]}
        corrected_through = cls._corrected_through(reversed([
            row for row in tables["session_events"] if row["event_type"] == "training_credit_rebuilt"
        ]))
        legacy = sorted({
            questions[row["question_id"]] for row in tables["attempts"]
            if row["status"] == "evaluated" and not row["is_followup"] and row["id"] > corrected_through
            and row["question_id"] in questions
            and cls._metadata(row["evaluation_json"]).get("credit_policy") != CREDIT_POLICY_VERSION
        })
        receipt_session = max(ordered, key=lambda item: item[:2])[2]["session_id"] if ordered else (
            tables["sessions"][-1]["id"] if tables["sessions"] else None
        )
        if (changes or legacy) and receipt_session is None:
            blockers.append({"reason": "No existing session can own a correction receipt; no session is invented"})
        return {
            "database": str(path), "policy": CREDIT_POLICY_VERSION,
            "source_digest": digest, "changes": changes,
            "unverified_attempts": issues, "blockers": blockers,
            "through_attempt_id": max((row["id"] for row in tables["attempts"]), default=0),
            "legacy_competencies": legacy, "needs_receipt": bool(legacy),
            "receipt_session_id": receipt_session,
            "limits": {"rows_per_evidence_table": MAX_REBUILD_ROWS, "profile_bytes": MAX_REBUILD_BYTES},
        }

    @classmethod
    def preview_credit_rebuild(cls, path: Path) -> dict:
        """Explicit existing path, read-only snapshot, no store initialization."""
        path, connection = cls._open_credit_database(path, readonly=True)
        try:
            before = (path.stat().st_size, path.stat().st_mtime_ns)
            report = cls._credit_projection(connection, path)
            if Path(str(path) + "-wal").exists() or before != (path.stat().st_size, path.stat().st_mtime_ns):
                raise ValueError("Profile changed during preview; stop writers or preview a consistent copy")
            return {**report, "applied": False}
        finally:
            connection.close()

    @classmethod
    def apply_credit_rebuild(cls, path: Path, *, expected_digest: str, backup_path: Path | None = None) -> dict:
        path, connection = cls._open_credit_database(path, readonly=False)
        backup = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            report = cls._credit_projection(connection, path)
            if report["blockers"]:
                raise ValueError("Unreconstructable records block apply; inspect the preview")
            if not report["changes"] and not report["needs_receipt"]:
                connection.rollback()
                return {**report, "applied": False, "already_current": True}
            if report["source_digest"] != expected_digest:
                raise ValueError("Profile changed since the reviewed preview; preview again before apply")
            backup = Path(backup_path) if backup_path else path.with_name(f"{path.name}.credit-backup-{uuid4().hex}.db")
            backup = backup.expanduser().resolve()
            if backup == path or backup.exists() or not backup.parent.is_dir():
                raise ValueError("Backup must be a new file in an existing directory")
            # Reserve the destination; never replace an existing user file.
            with backup.open("xb"):
                pass
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(backup)) as destination:
                    source.backup(destination)
            # BEGIN IMMEDIATE prevents another writer changing the committed
            # source between projection, backup and this atomic correction.
            now = iso_now()
            assignments = ",".join(f"{field}=?" for field in CREDIT_FIELDS)
            for name, change in report["changes"].items():
                connection.execute(
                    f"UPDATE competencies SET {assignments},updated_at=? WHERE name=?",
                    (*[change["after"][field] for field in CREDIT_FIELDS], now, name),
                )
            receipt = {**report, "backup": str(backup), "applied_at": now}
            connection.execute(
                "INSERT INTO session_events(session_id,event_type,detail,created_at) VALUES(?,'training_credit_rebuilt',?,?)",
                (report["receipt_session_id"], json.dumps(receipt, sort_keys=True), now),
            )
            connection.commit()
            return {**report, "applied": True, "backup": str(backup)}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
        eligibility = assessment_eligibility(evaluation)
        assessed = assessment_outcome(evaluation, evaluation.outcome)
        return {
            "credit_policy": CREDIT_POLICY_VERSION,
            "assessment_eligible": eligibility.assessed,
            "eligibility_reason": eligibility.reason,
            "assessment_outcome": assessed.value if assessed else None,
            "diagnostic_outcome": evaluation.outcome.value,
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
