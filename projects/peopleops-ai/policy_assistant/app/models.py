"""Typed contracts for the offline enterprise reference runtime."""
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(Strict):
    employee_id: str
    slack_user_id: str
    team_id: str
    tenant: str
    role: Literal["employee", "hr_admin", "admin"]
    country: Literal["US", "UK"]
    groups: list[str]
    permissions: list[str]
    record_scope: list[str] = Field(default_factory=list)
    delegation_purpose: str | None = None
    active: bool = True


class Intent(StrEnum):
    POLICY_QUESTION = "POLICY_QUESTION"
    PTO_BALANCE = "PTO_BALANCE"
    BENEFITS_QUESTION = "BENEFITS_QUESTION"
    PAYROLL_POLICY = "PAYROLL_POLICY"
    EMPLOYEE_DATA_REQUEST = "EMPLOYEE_DATA_REQUEST"
    UNSUPPORTED_REQUEST = "UNSUPPORTED_REQUEST"
    AMBIGUOUS_REQUEST = "AMBIGUOUS_REQUEST"


class Route(Strict):
    intent: Intent
    target_employee: str | None = None
    personal_review: bool = False
    rule_id: str = ""


class DocumentMetadata(Strict):
    document_id: str = Field(pattern=r"^HR-[A-Z0-9-]+$")
    title: str = Field(min_length=1, max_length=160)
    category: str
    policy_key: str
    source_system: Literal["mock_hr_portal"]
    country: Literal["US", "UK", "ALL"]
    employee_group: str
    access_roles: list[Literal["employee", "hr_admin", "admin"]] = Field(min_length=1)
    classification: Literal["public", "internal", "restricted", "confidential"]
    version: str = Field(pattern=r"^\d{1,3}\.\d{1,3}$")
    status: Literal["approved", "draft", "revoked", "superseded"]
    effective_date: date
    expiration_date: date | None = None
    owner: str = Field(min_length=1)
    tenant: str
    facts: dict[str, str | int | float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.expiration_date and self.expiration_date <= self.effective_date:
            raise ValueError("Expiration must follow effective date")
        return self


class Document(DocumentMetadata):
    text: str = Field(min_length=1, max_length=100_000, validation_alias=AliasChoices("text", "content"))


class PTORecord(Strict):
    employee_id: str
    tenant: str
    pto_balance: Decimal = Field(ge=0, allow_inf_nan=False)
    unit: Literal["days", "hours"]
    as_of_date: date
    source_system: Literal["mock_workday"] = "mock_workday"

    @field_validator("pto_balance", mode="before")
    @classmethod
    def numeric_balance(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("PTO balance must be a JSON number")
        return Decimal(str(value))


class AskRequest(Strict):
    question: str = Field(min_length=3, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Blank question")
        return value.strip()


class SlackEvent(Strict):
    type: Literal["app_mention"]
    user: str
    text: str = Field(min_length=3, max_length=2000)


class SlackEnvelope(Strict):
    type: Literal["event_callback"]
    team_id: str
    event_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    event: SlackEvent


class SourceCitation(Strict):
    document_id: str
    policy_id: str
    title: str
    version: str
    chunk_id: str
    section: str
    quote: str
    source: str
    effective_on: date


class ExecutionStage(Strict):
    stage: str
    status: Literal["passed", "failed", "denied", "handled", "skipped", "replayed"]
    duration_ms: float = Field(ge=0)
    rule_ids: list[str] = Field(default_factory=list)
    failure_code: str | None = None


class RuleMatch(Strict):
    rule_id: str
    kind: Literal["business", "routing", "security"]
    source: str
    description: str
    outcome: str
    requirement_ids: list[str]


class SourceAccess(Strict):
    system: Literal["identity_service", "hr_policy_index", "mock_workday_database"]
    access: Literal["accessed", "blocked", "not_selected"]
    operation: str
    duration_ms: float = Field(ge=0)
    attempts: int = Field(default=0, ge=0)
    returned_count: int = Field(default=0, ge=0)
    freshness: str = "not_accessed"
    fields: list[str] = Field(default_factory=list)


class SimulationRequest(AskRequest):
    scenario: Literal["normal", "unavailable", "timeout", "missing", "malformed", "stale", "wrong_owner", "rate_limited", "intermittent", "slow"] = "normal"


class TestRunRequest(Strict):
    suite: Literal["unit", "integration", "security", "evaluations"]


class HRResponse(Strict):
    status: Literal["answered", "denied", "abstained", "clarify", "escalated", "refused", "unavailable"]
    answer: str
    intent: Intent
    citations: list[SourceCitation] = Field(default_factory=list)
    facts: dict[str, str] = Field(default_factory=dict)
    escalation: str | None = None
    request_id: str = ""
    requirement_ids: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    execution_trace: list[ExecutionStage] = Field(default_factory=list)
    sources: list[SourceAccess] = Field(default_factory=list)
    applied_rules: list[RuleMatch] = Field(default_factory=list)
    failure_code: str | None = None
    handled_safely: bool = True
    replayed: bool = False
    duration_ms: float = Field(default=0, ge=0)
    mode: str = "Enterprise mock · deterministic sources"
