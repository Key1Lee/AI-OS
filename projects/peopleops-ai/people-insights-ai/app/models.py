"""Small, explicit request contracts; identities are resolved by the server."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEPARTMENTS = ("Sales", "Research & Development", "Human Resources")
Department = Literal["Sales", "Research & Development", "Human Resources"]
Metric = Literal[
    "job_satisfaction", "work_life_balance", "attrition", "overtime", "engagement"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=2000)


class ReportRequest(StrictModel):
    department: Department | None = None
    departments: list[Department] | None = Field(
        default=None, min_length=1, max_length=3
    )
    metrics: list[Metric] = Field(min_length=1, max_length=5)
    source: Literal["ibm", "qualtrics"] = "ibm"

    @model_validator(mode="after")
    def one_department_field(self):
        if (self.department is None) == (self.departments is None):
            raise ValueError("Provide department or departments, but not both")
        return self

    def selected_departments(self):
        return list(dict.fromkeys(self.departments or [self.department]))


class QualtricsImport(StrictModel):
    csv_text: str = Field(min_length=1, max_length=200_000)
    synthetic_demo: Literal[True]
    authorized_aggregate: Literal[True]


class MetricResult(BaseModel):
    key: Metric
    label: str
    value: float | None
    average: float | None = None
    numerator: int | None = None
    denominator: int | None
    missing: int | None = None
    formula: str
    kind: Literal["favorable", "observed", "provided"]
    status: Literal["ready", "suppressed", "provided"]
    unit: Literal["percent"] = "percent"


class DepartmentResult(BaseModel):
    department: Department
    employees: int | None
    status: Literal["ready", "suppressed", "provided"]
    metrics: dict[Metric, MetricResult]


class ReportResult(BaseModel):
    title: str
    source: dict[str, Any]
    metrics: list[Metric]
    departments: list[DepartmentResult]
    summary: str
    limitations: str
    report_id: str
    csv_url: str


class ChatResult(BaseModel):
    status: Literal["report", "clarification", "unsupported", "error"]
    message: str
    options: list[str]
    report: ReportResult | None
    context: dict[str, Any] | None = None
    elapsed_ms: float | None = None
    execution_mode: Literal["direct", "n8n"] | None = None


class ReportResponse(BaseModel):
    status: Literal["report"]
    report: ReportResult
    elapsed_ms: float
