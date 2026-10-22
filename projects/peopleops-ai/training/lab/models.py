"""One declarative schema; row grains and metric definitions are in docs/data.md."""
from datetime import date, datetime
from typing import Any
from sqlalchemy import Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import VECTOR


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"
    employee_id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    department: Mapped[str]
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.employee_id"))
    status: Mapped[str]
    hire_date: Mapped[date] = mapped_column(Date)
    termination_date: Mapped[date | None] = mapped_column(Date)
    pto_hours: Mapped[int]
    benefits_eligible: Mapped[bool]
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("pto_hours >= 0"), CheckConstraint("status IN ('active','leave','terminated','prehire')"))


class Job(Base):
    __tablename__ = "jobs"
    job_id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    department: Mapped[str]
    status: Mapped[str]
    opened_on: Mapped[date] = mapped_column(Date)


class Candidate(Base):
    __tablename__ = "candidates"
    candidate_id: Mapped[str] = mapped_column(primary_key=True)
    full_name: Mapped[str]
    email: Mapped[str]
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id"))


class RecruitingEvent(Base):
    __tablename__ = "recruiting_events"
    event_id: Mapped[str] = mapped_column(primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.candidate_id"))
    stage: Mapped[str]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Policy(Base):
    __tablename__ = "policies"
    policy_id: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str]
    audience: Mapped[str]
    effective_on: Mapped[date] = mapped_column(Date)
    retired: Mapped[bool] = mapped_column(default=False)


class PolicySection(Base):
    __tablename__ = "policy_sections"
    section_key: Mapped[str] = mapped_column(primary_key=True)
    policy_id: Mapped[str]
    version: Mapped[int]
    section_id: Mapped[str]
    heading: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["policy_id", "version"], ["policies.policy_id", "policies.version"]),
        UniqueConstraint("policy_id", "version", "section_id"),
    )


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    chunk_id: Mapped[str] = mapped_column(primary_key=True)
    section_key: Mapped[str] = mapped_column(ForeignKey("policy_sections.section_key"))
    body: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(64))


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    category: Mapped[str]
    subject: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    task_id: Mapped[str] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    kind: Mapped[str]
    status: Mapped[str]
    due_on: Mapped[date] = mapped_column(Date)
    __table_args__ = (UniqueConstraint("employee_id", "kind"),)


class Proposal(Base):
    __tablename__ = "action_proposals"
    proposal_id: Mapped[str] = mapped_column(primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    tool: Mapped[str]
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON)
    payload_hash: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActionReceipt(Base):
    __tablename__ = "action_receipts"
    receipt_id: Mapped[str] = mapped_column(primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("action_proposals.proposal_id"), unique=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    idempotency_key: Mapped[str]
    payload_hash: Mapped[str]
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("actor_id", "idempotency_key"),)


class PTORequest(Base):
    __tablename__ = "pto_requests"
    request_id: Mapped[str] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    hours: Mapped[int]
    status: Mapped[str]
    __table_args__ = (CheckConstraint("hours > 0"), CheckConstraint("end_date >= start_date"))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    event_id: Mapped[str] = mapped_column(primary_key=True)
    actor_id: Mapped[str]
    action: Mapped[str]
    target_id: Mapped[str]
    outcome: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SeedMarker(Base):
    __tablename__ = "seed_markers"
    version: Mapped[str] = mapped_column(primary_key=True)
