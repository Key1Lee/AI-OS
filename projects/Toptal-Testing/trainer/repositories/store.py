from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from urllib.parse import quote

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from trainer.config import ROOT
from trainer.exercises.bank import Bank, content_hash
from trainer.repositories.models import CompetencyRow, ExerciseVersionRow, MasteryRow
from trainer.mastery.policy import empty_state


class Store:
    """Transaction boundary. Domain code receives sessions, never raw SQL strings."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size:
            connection = sqlite3.connect(f"file:{quote(str(path.resolve()))}?mode=ro",uri=True)
            try:
                tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} - {"sqlite_sequence"}
                expected = {"alembic_version","exercise_versions","attempt_submissions","mastery"}
                if tables and not expected.issubset(tables):
                    raise ValueError("This database belongs to another application or is an incomplete migration. Choose a new AE_TRAINER_DB profile; existing data was not changed.")
            finally:
                connection.close()
        self.path = path
        self.engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 15})

        @event.listens_for(self.engine, "connect")
        def sqlite_settings(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=15000")

    def migrate(self):
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    @contextmanager
    def transaction(self, *, write=False):
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                if write:
                    # Serialize single-user writes across tabs/processes. Read-only
                    # queries remain possible under WAL; execution occurs outside.
                    session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def seed(self, bank: Bank):
        with self.transaction(write=True) as session:
            for competency in bank.competencies.values():
                row = session.get(CompetencyRow, competency.id)
                if row is None:
                    session.add(CompetencyRow(id=competency.id, definition=competency.model_dump()))
                else:
                    row.definition = competency.model_dump()
            session.flush()
            for competency in bank.competencies.values():
                if session.get(MasteryRow, competency.id) is None:
                    session.add(MasteryRow(competency_id=competency.id, state=empty_state()))
            for exercise in bank.exercises.values():
                key = f"{exercise.id}:v{exercise.version}"
                row = session.get(ExerciseVersionRow, key)
                digest = content_hash(exercise)
                if row and row.content_hash != digest:
                    raise ValueError(f"Exercise {key} changed without a version bump; history remains unchanged.")
                if row is None:
                    session.add(ExerciseVersionRow(id=key, exercise_id=exercise.id, version=exercise.version, content_hash=digest, definition=exercise.model_dump()))
