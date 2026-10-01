from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CompetencyRow(Base):
    __tablename__ = "competencies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    definition: Mapped[dict] = mapped_column(JSON)


class ExerciseVersionRow(Base):
    __tablename__ = "exercise_versions"
    __table_args__ = (UniqueConstraint("exercise_id", "version"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    exercise_id: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String)
    definition: Mapped[dict] = mapped_column(JSON)


class SessionRow(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mode: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    completed_at: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")


class AttemptRow(Base):
    __tablename__ = "attempts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    exercise_version_id: Mapped[str] = mapped_column(ForeignKey("exercise_versions.id"))
    parent_attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.id"))
    mode: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")
    started_at: Mapped[str] = mapped_column(String)
    completed_at: Mapped[str | None] = mapped_column(String)
    code: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    external_assistance: Mapped[bool] = mapped_column(Boolean, default=False)
    solution_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    hint_count: Mapped[int] = mapped_column(Integer, default=0)
    draft_revision: Mapped[int] = mapped_column(Integer, default=0)
    timed: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict | None] = mapped_column(JSON)
    selection: Mapped[dict] = mapped_column(JSON, default=dict)


class SubmissionRow(Base):
    __tablename__ = "attempt_submissions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    created_at: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    external_assistance: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String)
    result: Mapped[dict | None] = mapped_column(JSON)


class TestRunRow(Base):
    __tablename__ = "test_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    kind: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)
    result: Mapped[dict] = mapped_column(JSON)


class InteractionRow(Base):
    __tablename__ = "interactions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    kind: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class MasteryRow(Base):
    __tablename__ = "mastery"
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.id"), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON)


class MistakeRow(Base):
    __tablename__ = "mistakes"
    __table_args__ = (UniqueConstraint("competency_id", "category"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.id"), index=True)
    category: Mapped[str] = mapped_column(String)
    state: Mapped[dict] = mapped_column(JSON)


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.id"), index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
