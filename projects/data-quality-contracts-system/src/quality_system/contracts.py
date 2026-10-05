from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["PASS", "WARN", "FAIL", "UNKNOWN"]
Severity = Literal["INFO", "WARNING", "CRITICAL"]
DataType = Literal["STRING", "INTEGER", "DECIMAL", "TIMESTAMP", "BOOLEAN"]
Name = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,79}$")]
Rate = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False, max_digits=40, decimal_places=38)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


def aware(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError("Expected an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must have an explicit timezone")
    return value


class Column(Contract):
    name: Name
    data_type: DataType
    nullable: bool
    required: bool = True
    description: str = ""
    precision: int = Field(default=18, ge=1, le=38)
    scale: int = Field(default=2, ge=0, le=18)

    @model_validator(mode="after")
    def decimal_shape(self):
        if self.scale > self.precision:
            raise ValueError("Scale must not exceed precision")
        return self


class Unique(Contract):
    kind: Literal["unique"] = "unique"
    columns: list[Name] = Field(min_length=1, max_length=4)
    null_policy: Literal["ignore", "fail"] = "fail"

    @field_validator("columns")
    @classmethod
    def distinct_columns(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Key columns must be distinct")
        return value


class NotNull(Contract):
    kind: Literal["not_null"] = "not_null"
    column: Name
    minimum_rate: Rate = Decimal("1")


class AcceptedValues(Contract):
    kind: Literal["accepted_values"] = "accepted_values"
    column: Name
    values: list[str | int | bool] = Field(min_length=1, max_length=40)
    allow_null: bool = False


class Relationship(Contract):
    kind: Literal["relationship"] = "relationship"
    column: Name
    parent_dataset: Name
    parent_column: Name
    allow_null: bool = False
    require_unique_parent: bool = True
    maximum_orphan_rate: Rate = Decimal("0")


class Schema(Contract):
    kind: Literal["schema"] = "schema"
    allow_extra_columns: bool = True


class Business(Contract):
    kind: Literal["business_rule"] = "business_rule"
    invariant: Literal["completed_is_paid", "non_negative_revenue", "shipment_after_order"]


class Freshness(Contract):
    kind: Literal["freshness"] = "freshness"
    maximum_age_minutes: int = Field(ge=0, le=525600)


class Volume(Contract):
    kind: Literal["volume"] = "volume"
    minimum: int = Field(ge=0, le=1000000000)
    maximum: int = Field(ge=0, le=1000000000)

    @model_validator(mode="after")
    def ordered(self):
        if self.minimum > self.maximum:
            raise ValueError("Minimum volume must not exceed maximum")
        return self


class Reconciliation(Contract):
    kind: Literal["reconciliation"] = "reconciliation"
    column: Name = "net_revenue"
    source_dataset: Name = "payments"
    source_column: Name = "amount"
    adjustment_dataset: Name = "returns"
    adjustment_column: Name = "refund_amount"
    absolute_tolerance: Decimal = Field(default=Decimal("0.01"), ge=0, allow_inf_nan=False)
    relative_tolerance: Rate = Decimal("0")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")


Expectation = Annotated[Unique | NotNull | AcceptedValues | Relationship | Schema |
                        Business | Freshness | Volume | Reconciliation, Field(discriminator="kind")]


class QualityRule(Contract):
    id: Name
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=1000)
    target: Name
    target_type: Literal["dataset", "column"] = "dataset"
    dimension: Literal["schema", "completeness", "uniqueness", "validity", "consistency",
                       "referential_integrity", "freshness", "volume", "business_rule", "reconciliation"]
    expectation: Expectation
    severity: Severity = "CRITICAL"
    blocking: bool = True
    owner: str = Field(default="Commerce Analytics", min_length=1, max_length=150)
    evidence_source: str = "deterministic_dataset"

    @model_validator(mode="after")
    def dimension_matches(self):
        allowed = {"schema": {"schema"}, "unique": {"uniqueness"}, "not_null": {"completeness"},
                   "accepted_values": {"validity"}, "relationship": {"referential_integrity"},
                   "business_rule": {"business_rule", "consistency"}, "freshness": {"freshness"},
                   "volume": {"volume"}, "reconciliation": {"reconciliation"}}
        if self.dimension not in allowed[self.expectation.kind]:
            raise ValueError("Dimension does not match expectation kind")
        return self


class DataContract(Contract):
    contract_version: Literal["data-contract-v1"] = "data-contract-v1"
    id: Name
    version: str = Field(default="1.0", min_length=1, max_length=40)
    dataset_id: Name
    grain: str = Field(min_length=1, max_length=200)
    primary_key: list[Name] = Field(min_length=1, max_length=4)
    columns: list[Column] = Field(min_length=1, max_length=50)
    relationships: list[Relationship] = Field(default_factory=list, max_length=20)
    rules: list[QualityRule] = Field(default_factory=list, max_length=50)
    owner: str = Field(min_length=1, max_length=150)
    semantic_meaning: str = Field(min_length=1, max_length=2000)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def coherent(self):
        columns = {c.name: c for c in self.columns}
        if len(columns) != len(self.columns):
            raise ValueError("Contract column names must be unique")
        if len(self.primary_key) != len(set(self.primary_key)):
            raise ValueError("Primary key columns must be distinct")
        if any(k not in columns or columns[k].nullable or not columns[k].required for k in self.primary_key):
            raise ValueError("Primary keys must be required, non-null contract columns")
        if any(r.column not in columns for r in self.relationships):
            raise ValueError("Relationship column must exist in contract")
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Rule IDs must be unique")
        if any(r.target != self.dataset_id for r in self.rules):
            raise ValueError("Contract rules must target its dataset")
        return self


class Dataset(Contract):
    id: Name
    columns: list[Column] | None = Field(default=None, max_length=50)
    rows: list[dict[str, Any]] | None = Field(default=None, max_length=200)
    loaded_at: str | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def distinct_columns(self):
        if self.columns is not None and len({c.name for c in self.columns}) != len(self.columns):
            raise ValueError("Observed column names must be unique")
        return self


class Evidence(Contract):
    classification: Literal["FACT"] = "FACT"
    source: str = "deterministic_quality_engine"
    method: str
    message: str
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(Contract):
    contract_version: Literal["validation-result-v1"] = "validation-result-v1"
    rule_id: Name
    target_id: Name
    status: Status
    expected: Any
    actual: Any
    failed_rows: int | None = Field(ge=0)
    total_rows: int | None = Field(ge=0)
    failure_rate: str | None
    severity: Severity
    blocking: bool
    executed_at: str
    run_id: str
    input_fingerprint: str
    evidence: Evidence


class QualityEvent(Contract):
    contract_version: Literal["quality-event-v1"] = "quality-event-v1"
    dataset_id: Name
    rule_id: Name
    status: Status
    severity: Severity
    expected: Any
    actual: Any
    failure_count: int | None = Field(ge=0)
    total_rows: int | None = Field(ge=0)
    timestamp: str
    run_id: str
    input_fingerprint: str
    evidence: Evidence


class QualityGate(Contract):
    contract_version: Literal["quality-gate-v1"] = "quality-gate-v1"
    dataset_id: Name
    status: Literal["OPEN", "BLOCKED"]
    publication: Literal["ELIGIBLE", "WITHHELD"]
    blocking_rule_ids: list[str]
    reasons: list[str]
    run_id: str
    input_fingerprint: str


class ValidationBundle(Contract):
    contract_version: Literal["quality-bundle-v1"] = "quality-bundle-v1"
    contract: DataContract
    rules: list[QualityRule]
    results: list[ValidationResult]
    gate: QualityGate
    events: list[QualityEvent]
    summary: dict[str, int]
    run_id: str
    input_fingerprint: str


class ValidateRequest(Contract):
    contract: DataContract
    datasets: dict[str, Dataset] = Field(max_length=20)
    executed_at: str
    run_id: str = Field(min_length=1, max_length=100)
    additional_rules: list[QualityRule] = Field(default_factory=list, max_length=10)
    rule_ids: list[Name] | None = Field(default=None, max_length=80)

    _aware = field_validator("executed_at")(aware)

    @model_validator(mode="after")
    def dataset_identity(self):
        if any(key != value.id for key, value in self.datasets.items()):
            raise ValueError("Dataset map keys must match dataset IDs")
        return self
