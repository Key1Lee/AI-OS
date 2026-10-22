from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Identity(StrictModel):
    subject: str = Field(min_length=1, max_length=100)
    tenant: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    region: str = Field(pattern=r"^[A-Z]{2}$")
    role: Literal["employee", "manager", "hr", "admin"]


class Credential(StrictModel):
    token_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    identity: Identity


class PolicyMetadata(StrictModel):
    policy_id: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=160)
    effective_on: date
    expires_on: date | None = None
    regions: list[str] = Field(min_length=1, max_length=30)
    roles: list[Literal["employee", "manager", "hr", "admin"]] = Field(min_length=1, max_length=4)
    withdrawn: bool = False

    @model_validator(mode="after")
    def valid_dates_and_regions(self):
        if self.expires_on and self.expires_on <= self.effective_on:
            raise ValueError("expires_on must follow effective_on")
        if any(r != "*" and not re.fullmatch(r"[A-Z]{2}", r) for r in self.regions):
            raise ValueError("regions must be two-letter uppercase codes or *")
        return self


class PolicyFile(StrictModel):
    filename: str = Field(pattern=r"^[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,99}\.md$")
    markdown: str = Field(min_length=1, max_length=100_000)


class IngestRequest(StrictModel):
    documents: list[PolicyFile] = Field(min_length=1, max_length=20)


class Question(StrictModel):
    question: str = Field(min_length=3, max_length=2000)


class Citation(StrictModel):
    policy_id: str
    version: int
    title: str
    section: str
    chunk_id: str
    source: str
    effective_on: date
    quote: str


class Answer(StrictModel):
    status: Literal["answered", "abstained", "escalated", "refused", "unavailable"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    escalation: str | None = None
    request_id: str = ""
    mode: str = ""


class Selection(StrictModel):
    supported: bool
    chunk_ids: list[str] = Field(max_length=3)
