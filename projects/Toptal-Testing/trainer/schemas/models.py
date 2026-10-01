from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Identifier = str


class Column(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: Literal["BIGINT", "INTEGER", "DOUBLE", "DECIMAL(18,2)", "VARCHAR", "BOOLEAN", "DATE", "TIMESTAMP", "TIMESTAMPTZ"]


class Table(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    columns: list[Column] = Field(min_length=1, max_length=40)
    rows: list[list[Any]] = Field(max_length=10000)

    @model_validator(mode="after")
    def valid_shape(self):
        if len({c.name for c in self.columns}) != len(self.columns):
            raise ValueError("Duplicate column name")
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("Fixture row does not match column count")
        return self


class TestCase(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    category: str
    tables: list[Table] = Field(min_length=1)
    expected_rows: list[list[Any]]
    diagnostic: str
    competencies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_tables(self):
        if len({t.name for t in self.tables}) != len(self.tables):
            raise ValueError("Duplicate fixture table name")
        return self


class ClarificationRule(StrictModel):
    topic: str
    keywords: list[str]
    response: str


class FollowUp(StrictModel):
    title: str
    prompt: str


class Exercise(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    version: int = Field(ge=1)
    title: str
    type: Literal["sql"] = "sql"
    domain: str
    family: str
    competencies: list[str] = Field(min_length=1)
    difficulty: int = Field(ge=1, le=6)
    estimated_duration: int = Field(ge=1)
    prompt: str
    context: str
    starter_code: str = "-- Write your query here\n"
    expected_columns: list[str] = Field(min_length=1)
    expected_types: list[Literal["INTEGER","NUMERIC","VARCHAR","DATE","TIMESTAMP","TIMESTAMPTZ","BOOLEAN"]] = Field(default_factory=list)
    ordered: bool = False
    float_tolerance: float = Field(default=0.000001, ge=0, le=0.01)
    visible_case: TestCase
    hidden_cases: list[TestCase] = Field(min_length=1)
    reference_solution: str
    solution_explanation: str
    senior_review: str
    hints: list[str] = Field(min_length=3, max_length=3)
    clarification_rules: list[ClarificationRule] = Field(default_factory=list)
    follow_up_variants: list[FollowUp] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str = "2026-10-01"
    updated_at: str = "2026-10-01"

    @model_validator(mode="after")
    def valid_cases(self):
        cases = [self.visible_case, *self.hidden_cases]
        if self.expected_types and len(self.expected_types) != len(self.expected_columns):
            raise ValueError("Expected type count does not match output columns")
        if len({c.id for c in cases}) != len(cases):
            raise ValueError("Duplicate test case ID")
        if any(len(row) != len(self.expected_columns) for c in cases for row in c.expected_rows):
            raise ValueError("Expected row does not match output columns")
        for c in cases:
            if not set(c.competencies).issubset(self.competencies):
                raise ValueError("Case tests an unrelated competency")
            shape = [(t.name, t.columns) for t in c.tables]
            if shape != [(t.name, t.columns) for t in self.visible_case.tables]:
                raise ValueError("Case schema differs from the frozen public schema")
        return self

    def public(self) -> dict:
        fields = {"id", "version", "title", "type", "domain", "family", "competencies", "difficulty", "estimated_duration", "prompt", "context", "starter_code", "expected_columns", "expected_types", "prerequisites", "tags"}
        view = self.model_dump(include=fields)
        view["tables"] = [t.model_dump() for t in self.visible_case.tables]
        view["clarification_topics"] = [r.topic for r in self.clarification_rules]
        return view


class Competency(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    category: str
    name: str
    description: str
    importance: int = Field(ge=1, le=5)
    prerequisites: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    progression: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])


class StartRequest(StrictModel):
    mode: Literal["adaptive", "practice", "interview"] = "adaptive"
    exercise_id: str | None = None
    competency: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=6)
    timed: bool = False


class DraftRequest(StrictModel):
    code: str = Field(max_length=100000)
    explanation: str = Field(default="", max_length=16000)
    external_assistance: bool = False
    revision: int = Field(ge=0)


class RunRequest(StrictModel):
    code: str = Field(min_length=1, max_length=100000)


class SubmitRequest(RunRequest):
    request_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    explanation: str = Field(default="", max_length=16000)
    external_assistance: bool = False


class ClarificationRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)


class ReasoningEvidence(StrictModel):
    rubric_scores: dict[str, int]
    strengths: list[str]
    weaknesses: list[str]
    misconceptions: list[str]
    feedback: str
    seniority_signals: list[str]
    missing_seniority_signals: list[str]

    @field_validator("rubric_scores",mode="before")
    @classmethod
    def strict_integer_scores(cls, value):
        if not isinstance(value,dict) or any(type(score) is not int for score in value.values()):
            raise ValueError("Rubric scores must be actual integers, not coerced strings or booleans")
        return value

    @model_validator(mode="after")
    def validate_scores(self):
        required = {"problem_understanding", "correctness_reasoning", "tradeoff_reasoning", "production_awareness", "communication"}
        if set(self.rubric_scores) != required:
            raise ValueError("Incomplete or unexpected reasoning rubric")
        if any(type(score) is not int or not 0 <= score <= 4 for score in self.rubric_scores.values()):
            raise ValueError("Rubric scores must be integers from 0 to 4")
        return self
