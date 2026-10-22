from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["employee", "manager", "recruiter", "hr_admin", "analyst"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Principal(Contract):
    employee_id: str
    role: Role


class EmployeeRecord(Contract):
    employee_id: str
    full_name: str
    email: str
    department: str
    manager_id: str | None
    status: Literal["active", "leave", "terminated", "prehire"]
    hire_date: date
    termination_date: date | None
    pto_hours: int = Field(ge=0)
    benefits_eligible: bool
    source_updated_at: datetime


class EmployeeView(Contract):
    employee_id: str
    full_name: str
    department: str
    status: str
    pto_hours: int
    benefits_eligible: bool


class Question(Contract):
    text: str = Field(min_length=1, max_length=2000)


class CandidateView(Contract):
    candidate_id: str
    full_name: str
    email: str
    job_id: str


class JobView(Contract):
    job_id: str
    title: str
    department: str
    status: str
    opened_on: date


class RequestStatus(Contract):
    request_id: str
    type: Literal["pto", "ticket"]
    status: str


class Citation(Contract):
    policy_id: str
    section_id: str
    version: int
    quote: str


class Answer(Contract):
    status: Literal["answered", "refused", "clarify"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved_ids: list[str] = Field(default_factory=list)


class Plan(Contract):
    tool: Literal["create_pto", "create_ticket", "request_status", "clarify"]
    arguments: dict[str, Any]
    summary: str


class Confirmation(Contract):
    proposal_id: str
    confirmed: bool
    idempotency_key: str = Field(min_length=8, max_length=128)


class ActionResult(Contract):
    request_id: str
    status: str
    replayed: bool = False


class Page(Contract):
    items: list[dict[str, Any]]
    next_cursor: int | None
    schema_version: int = 1


class Health(Contract):
    status: str
    mode: str = "synthetic-training"


class PendingExercise(NotImplementedError):
    def __init__(self, exercise: str):
        self.exercise = exercise
        super().__init__(f"Implement {exercise}; see docs/exercises.md")
