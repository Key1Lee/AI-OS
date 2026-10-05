from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["pass", "warning", "fail", "unknown"]
Cardinality = Literal["1:1", "1:N", "N:1", "N:N", "unknown"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GrainDefinition(Contract):
    declared: str | None = None
    label: str = "GRAIN UNKNOWN"
    evidence: str = "No learner declaration has been made."
    status: Status = "unknown"
    classification: Literal["declared", "inference", "unknown"] = "unknown"


class ColumnDefinition(Contract):
    name: str
    data_type: str
    nullable: bool = True
    description: str = ""


class TestResult(Contract):
    id: str
    name: str
    status: Status
    expected: Any = None
    actual: Any = None
    evidence: str


class ContractDefinition(Contract):
    grain: str
    primary_key: list[str]
    columns: list[ColumnDefinition]
    owner: str = "Analytics engineering"
    semantic_meaning: str


class ModelDefinition(Contract):
    id: str
    name: str
    layer: Literal["source", "staging", "intermediate", "fact", "dimension", "mart", "metric", "output"]
    why: str
    grain: GrainDefinition
    primary_key: list[str] = Field(default_factory=list)
    columns: list[ColumnDefinition] = Field(default_factory=list)
    row_count: int | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)
    materialization: str = "view"
    sql: str | None = None
    status: Status = "unknown"
    tests: list[TestResult] = Field(default_factory=list)


class RelationshipDefinition(Contract):
    id: str
    left_model: str
    right_model: str
    left_key: str
    right_key: str
    expected: Cardinality
    description: str


class TransformationStep(Contract):
    id: str
    input_model: str
    output_model: str
    operation: str
    why: str
    input_grain: str
    output_grain: str
    input_rows: int | None = None
    output_rows: int | None = None
    columns_added: list[str] = Field(default_factory=list)
    columns_removed: list[str] = Field(default_factory=list)
    columns_renamed: dict[str, str] = Field(default_factory=dict)
    filters: list[str] = Field(default_factory=list)
    joins: list[str] = Field(default_factory=list)
    aggregations: list[str] = Field(default_factory=list)
    windows: list[str] = Field(default_factory=list)
    tests: list[TestResult] = Field(default_factory=list)


class MetricDefinition(Contract):
    name: str
    description: str
    measure: str
    aggregation: Literal["SUM", "AVG", "COUNT"]
    time_dimension: str
    filters: list[str]
    dimensions: list[str]
    grain: str
    owner: str
    currency: str
    value: str | None = None
    expected_value: str = "225.00"
    status: Status = "unknown"
    evidence: str = "Not calculated."


class EvaluationResult(Contract):
    contract_version: str = "modeling-lab-v1"
    sql_valid: bool
    output_matches_expected: bool
    grain: GrainDefinition
    primary_key: dict[str, Any]
    tests: list[TestResult]
    warnings: list[str] = Field(default_factory=list)
    performance_notes: list[str] = Field(default_factory=list)
    status: Status
    explanation: str
    explanation_source: Literal["deterministic_evidence"] = "deterministic_evidence"


class GrainRequest(Contract):
    table: str = Field(min_length=1, max_length=80)
    grain: str = Field(min_length=1, max_length=80)
    primary_key: list[str] = Field(min_length=1, max_length=4)


class StagingRequest(Contract):
    source_grain: str = Field(min_length=1, max_length=80)


class BuildRequest(Contract):
    source_grain: str = Field(min_length=1, max_length=80)
    grain: str = Field(min_length=1, max_length=80)
    primary_key: list[str] = Field(default=["order_id"], min_length=1, max_length=4)
    strategy: Literal["safe", "fanout"] = "safe"
    sql: str | None = Field(default=None, min_length=1, max_length=10000)


class JoinRequest(Contract):
    left_table: str = "completed_orders"
    right_table: str = "order_items"
    left_key: str = "order_id"
    right_key: str = "order_id"
    kind: Literal["left", "inner"] = "left"
    aggregate_right: bool = False
    expected_cardinality: Cardinality = "N:1"
    expected_rows: int = Field(default=3, ge=0, le=1000)


class JoinTrace(Contract):
    key: Any
    left_rows: int
    right_rows: int
    output_rows: int
    repeated: bool
    order_amount: str | None = None
    contribution: str | None = None


class JoinResult(Contract):
    contract_version: str = "modeling-lab-v1"
    left_table: str
    right_table: str
    left_rows: int
    right_rows: int
    right_rows_after: int
    expected_cardinality: Cardinality
    actual_cardinality: Cardinality
    expected_rows: int
    calculated_rows: int
    actual_rows: int
    unmatched_left_rows: int
    null_left_keys: int
    null_right_keys: int
    left_grain: str
    right_grain: str
    resulting_grain: GrainDefinition
    fanout: bool
    baseline_amount: str | None
    joined_amount: str | None
    currency: str | None
    trace: list[JoinTrace]
    rows: list[dict[str, Any]]
    sql: str
    tests: list[TestResult]
    explanation: str
    explanation_source: Literal["deterministic_evidence"] = "deterministic_evidence"


class BuildResult(Contract):
    contract_version: str = "modeling-lab-v1"
    staging: ModelDefinition
    fact: ModelDefinition
    metric: MetricDefinition
    evaluation: EvaluationResult
    transformations: list[TransformationStep]
    inputs: list[ModelDefinition] = Field(default_factory=list)


class MetricRequest(Contract):
    build: BuildRequest
    name: str = Field(default="Revenue", min_length=1, max_length=80)
    aggregation: Literal["SUM", "AVG", "COUNT"] = "SUM"


class ScenarioDefinition(Contract):
    contract_version: str = "modeling-lab-v1"
    id: str
    title: str
    business_question: str
    business_definition: str
    sources: list[ModelDefinition]
    relationships: list[RelationshipDefinition]
    planned_models: list[ModelDefinition]
    transformations: list[TransformationStep]
    reference_sql: dict[str, str]
    fact_contract: ContractDefinition
    expected_revenue: str
    planned_metric: MetricDefinition


class GrainResult(Contract):
    model: ModelDefinition
    tests: list[TestResult]
    status: Status


class StagingResult(Contract):
    model: ModelDefinition
    transformation: TransformationStep
