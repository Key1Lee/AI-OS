"""Typed public contracts for the single bounded vertical slice."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from datetime import datetime
from uuid import UUID
from typing import Any, Protocol

SCENARIO_ID = "ORCH-IDEMPOTENCY-001"
CONTRACT_VERSION = "ae-lab-v1"

class State(StrEnum):
    READY = "READY"
    BASELINE = "BASELINE"
    FAULT_INJECTED = "FAULT_INJECTED"
    FAILED = "FAILED"
    DIAGNOSING = "DIAGNOSING"
    REMEDIATED = "REMEDIATED"
    VERIFIED = "VERIFIED"
    MASTERED = "MASTERED"

class EventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    ASSET_MATERIALIZED = "ASSET_MATERIALIZED"
    QUALITY_CHECK_PASSED = "QUALITY_CHECK_PASSED"
    QUALITY_CHECK_FAILED = "QUALITY_CHECK_FAILED"
    MODEL_COMPLETED = "MODEL_COMPLETED"
    MODEL_FAILED = "MODEL_FAILED"
    FRESHNESS_BREACH = "FRESHNESS_BREACH"
    SCHEMA_CHANGED = "SCHEMA_CHANGED"
    RUN_RETRIED = "RUN_RETRIED"
    INCIDENT_OPENED = "INCIDENT_OPENED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    RUN_COMPLETED = "RUN_COMPLETED"

@dataclass(frozen=True)
class Event:
    event_id: str
    timestamp: str
    run_id: str
    scenario_id: str
    system: str
    asset: str | None
    event_type: EventType
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)
    upstream_assets: tuple[str, ...] = ()
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self):
        UUID(self.run_id)
        stamp = datetime.fromisoformat(self.timestamp)
        if stamp.tzinfo is None:
            raise ValueError("Event timestamp must include a timezone")
        EventType(self.event_type)
        if not self.event_id or not self.system or not self.scenario_id:
            raise ValueError("Event identity, system and scenario are required")
        if self.status not in {"RUNNING", "SUCCESS", "PASS", "FAIL", "RETRYING", "FAILED", "HEALTHY", "VERIFIED"}:
            raise ValueError("Unknown canonical event status")
        if not isinstance(self.metadata, dict):
            raise ValueError("Event metadata must be an object")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

class ModelingAdapter(Protocol):
    def build(self, orders: list[dict], source: list[dict], run_id: str) -> dict: ...

class QualityAdapter(Protocol):
    def validate(self, orders: list[dict], run_id: str, timestamp: str) -> dict: ...

class ObservabilityAdapter(Protocol):
    def observe(self, evidence: dict, database: str) -> dict: ...

class TestingAdapter(Protocol):
    def evaluate(self, stage: str, answer: dict) -> dict: ...

class OrchestrationAdapter(Protocol):
    def schedule(self, run_id: str, fail_after_rows: int | None) -> dict: ...
