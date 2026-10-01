from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Classification = Literal["FACT", "INFERENCE", "AI_HYPOTHESIS"]
Status = Literal["HEALTHY", "WARNING", "FAILED", "UNKNOWN"]
Layer = Literal["source", "staging", "transformation", "mart", "output", "unknown"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(Contract):
    source: str
    pointer: str
    classification: Classification = "FACT"
    timestamp: str | None = None
    note: str | None = None


class Column(Contract):
    name: str
    data_type: str | None = None
    nullable: bool | None = None
    description: str | None = None
    tests: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)


class DataNode(Contract):
    id: str
    name: str
    namespace: str | None = None
    node_type: Literal["source", "model", "test", "output", "metric", "seed", "snapshot", "analysis"]
    layer: Layer = "unknown"
    description: str | None = None
    grain: str | None = None
    primary_keys: list[str] | None = None
    columns: list[Column] = Field(default_factory=list)
    status: Status = "UNKNOWN"
    owner: str | None = None
    source_system: str | None = None
    sql: str | None = None
    compiled_sql: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[Provenance] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_columns(self):
        if len({column.name for column in self.columns}) != len(self.columns):
            raise ValueError("Duplicate normalized column name")
        return self


class DataEdge(Contract):
    id: str
    from_node: str
    to_node: str
    relationship_type: Literal["depends_on", "tests"] = "depends_on"
    evidence_source: Provenance
    confidence: Literal["declared", "uncertain"] = "declared"
    inference_type: Classification = "FACT"


class Execution(Contract):
    node_id: str
    status: Status
    reported_status: str
    operation: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration: float | None = None
    error: str | None = None
    provenance: Provenance


class TestResult(Contract):
    node_id: str
    test_id: str
    test_name: str
    status: Status
    reported_status: str
    severity: str | None = None
    failures: int | None = None
    column: str | None = None
    association: Literal["confirmed", "ambiguous"] = "confirmed"
    evidence: str | None = None
    provenance: Provenance


class IncidentEvidence(Contract):
    node_id: str
    evidence_type: str
    expected: int | float | str | None = None
    actual: int | float | str | None = None
    comparison_key: str | None = None
    observation_id: str
    provenance: Provenance


class Issue(Contract):
    code: str
    message: str
    node_id: str | None = None
    provenance: Provenance


class GraphSnapshot(Contract):
    contract_version: str = "data-map-v1"
    system_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    name: str = Field(min_length=1, max_length=150)
    snapshot_id: str = ""
    nodes: list[DataNode]
    edges: list[DataEdge]
    executions: list[Execution] = Field(default_factory=list)
    tests: list[TestResult] = Field(default_factory=list)
    observations: list[IncidentEvidence] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    artifacts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sample: bool = False

    @model_validator(mode="after")
    def coherent(self):
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes) or len({edge.id for edge in self.edges}) != len(self.edges):
            raise ValueError("Duplicate graph identity")
        if len(ids) > 2000 or len(self.edges) > 10000:
            raise ValueError("This local release supports 2,000 nodes and 10,000 edges")
        if any(edge.from_node not in ids or edge.to_node not in ids for edge in self.edges):
            raise ValueError("Edge refers to an unknown node")
        if any(item.node_id not in ids for item in [*self.executions, *self.tests, *self.observations]):
            raise ValueError("Evidence refers to an unknown node")
        return self
