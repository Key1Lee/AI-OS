from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Mode(StrEnum):
    DAILY = "daily"
    COLD_RECALL = "cold_recall"
    PRACTICE = "practice"
    ASSESSMENT = "assessment"
    MOCK_INTERVIEW = "mock_interview"
    WEAKNESS_REVIEW = "weakness_review"


class Outcome(StrEnum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


class Assistance(StrEnum):
    NONE = "none"
    LIGHT = "light_hint"
    STRONG = "strong_hint"


class MasteryState(StrEnum):
    UNSEEN = "UNSEEN"
    WEAK = "WEAK"
    LEARNING = "LEARNING"
    DEVELOPING = "DEVELOPING"
    RELIABLE = "RELIABLE"
    MASTERED = "MASTERED"


@dataclass(frozen=True)
class Criterion:
    id: str
    description: str
    any_of: tuple[str, ...]
    weight: float = 1.0


@dataclass(frozen=True)
class Question:
    id: str
    competency: str
    family: str
    difficulty: int
    prompt: str
    criteria: tuple[Criterion, ...]
    hints: tuple[str, ...]
    followups: dict[str, str]
    source: str = "curated"


@dataclass(frozen=True)
class Evaluation:
    outcome: Outcome
    score: float
    met: tuple[str, ...]
    missing: tuple[str, ...]
    feedback: str
    misconception: str | None = None
    evaluator: str = "deterministic-rubric"
    evaluator_provider: str = "offline_fallback"
    evaluator_model: str = "deterministic-rubric-v1"
    evaluation_mode: str = "lexical_conservative"
    evaluation_confidence: str = "low"
    rubric_version: str = "senior-evaluator-v1"
    dimension_scores: dict[str, int] = field(default_factory=dict)
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    missed_concepts: tuple[str, ...] = ()
    critical_errors: tuple[str, ...] = ()
    unsupported_assumptions: tuple[str, ...] = ()
    follow_up_questions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    deterministic_results: dict[str, Any] = field(default_factory=dict)
    fallback_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Selection:
    question: Question
    reason: str
    is_cold_recall: bool = False
    is_transfer: bool = False
