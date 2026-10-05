from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from py_dev.providers.parsed import ParsedModelClient, credential_configured, select_evaluators, invoke_evaluators
from py_dev.providers.base import ProviderUnavailable
import uuid
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import Settings
from .deterministic import DeterministicReport, run_deterministic_checks
from .models import Evaluation, Mode, Outcome, Question


RUBRIC_VERSION = "senior-evaluator-v1"
PROMPT = (Path(__file__).with_name("prompts") / "evaluator.md").read_text(
    encoding="utf-8"
)


class Verdict(StrEnum):
    STRONG_PASS = "strong_pass"
    PASS = "pass"
    BORDERLINE = "borderline"
    FAIL = "fail"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CriterionStatus(StrEnum):
    MET = "met"
    PARTIAL = "partial"
    MISSING = "missing"
    INCORRECT = "incorrect"


class DimensionScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correctness: int = Field(ge=0, le=100)
    reasoning: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    engineering_judgment: int = Field(ge=0, le=100)
    communication: int = Field(ge=0, le=100)
    production_awareness: int = Field(ge=0, le=100)


class CriterionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    status: CriterionStatus
    evidence: list[str]
    analysis: str


class ReasoningEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: int = Field(ge=0, le=100)
    verdict: Verdict
    dimension_scores: DimensionScores
    strengths: list[str]
    weaknesses: list[str]
    missed_concepts: list[str]
    critical_errors: list[str]
    unsupported_assumptions: list[str]
    follow_up_questions: list[str]
    evidence: list[str]
    rubric_evidence: list[CriterionEvidence]
    evaluation_confidence: Confidence
    evaluator_provider: str = ""
    evaluator_model: str = ""


class EvaluationProvider(Protocol):
    name: str

    def evaluate(self, question: Question, answer: str, mode: Mode) -> Evaluation: ...


class LLMUnavailable(RuntimeError):
    pass


def _context(
    question: Question,
    answer: str,
    mode: Mode,
    deterministic: DeterministicReport,
) -> dict[str, Any]:
    return {
        "assessment_id": question.id,
        "mode": mode.value,
        "difficulty": question.difficulty,
        "problem": question.prompt,
        "rubric_version": RUBRIC_VERSION,
        "rubric": [
            {"id": item.id, "description": item.description, "weight": item.weight}
            for item in question.criteria
        ],
        "deterministic_results": deterministic.as_dict(),
        "candidate_answer": answer,
    }


def _outcome(verdict: Verdict) -> Outcome:
    if verdict in {Verdict.STRONG_PASS, Verdict.PASS}:
        return Outcome.PASS
    if verdict == Verdict.BORDERLINE:
        return Outcome.PARTIAL
    return Outcome.FAIL


def _to_evaluation(
    parsed: ReasoningEvaluation,
    *,
    question: Question,
    provider: str,
    model: str,
    deterministic: DeterministicReport,
    response_id: str | None = None,
) -> Evaluation:
    returned_ids = [item.criterion_id for item in parsed.rubric_evidence]
    expected_ids = {item.id for item in question.criteria}
    if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != expected_ids:
        raise LLMUnavailable(
            "Evaluator rubric evidence did not match the supplied rubric contract"
        )
    criterion_statuses = {
        item.criterion_id: item.status for item in parsed.rubric_evidence
    }
    met = tuple(
        criterion_id
        for criterion_id, status in criterion_statuses.items()
        if status == CriterionStatus.MET
    )
    missing = tuple(
        criterion_id
        for criterion_id, status in criterion_statuses.items()
        if status != CriterionStatus.MET
    )
    misconception = parsed.critical_errors[0] if parsed.critical_errors else None
    return Evaluation(
        outcome=_outcome(parsed.verdict),
        score=parsed.overall_score / 100,
        met=met,
        missing=missing,
        feedback="; ".join(parsed.weaknesses) or "No material weakness identified.",
        misconception=misconception,
        evaluator=f"{provider}:{model}:reasoning",
        evaluator_provider=provider,
        evaluator_model=model,
        evaluation_mode="reasoning",
        evaluation_confidence=parsed.evaluation_confidence.value,
        rubric_version=RUBRIC_VERSION,
        dimension_scores=parsed.dimension_scores.model_dump(),
        strengths=tuple(parsed.strengths),
        weaknesses=tuple(parsed.weaknesses),
        missed_concepts=tuple(parsed.missed_concepts),
        critical_errors=tuple(parsed.critical_errors),
        unsupported_assumptions=tuple(parsed.unsupported_assumptions),
        follow_up_questions=tuple(parsed.follow_up_questions),
        evidence=tuple(parsed.evidence),
        deterministic_results=deterministic.as_dict(),
        raw={
            "verdict": parsed.verdict.value,
            "rubric_evidence": [
                item.model_dump(mode="json") for item in parsed.rubric_evidence
            ],
            "response_id": response_id,
        },
    )


@dataclass
class OpenAIEvaluator:
    settings: Settings
    client: Any | None = None

    name: str = "openai"

    def __post_init__(self) -> None:
        if self.client is None and not credential_configured("openai"):
            raise LLMUnavailable("OpenAI credentials are not configured in AI-OS")
        self.transport = ParsedModelClient("openai", self.settings.model,
            calling_system="toptal.evaluator", client=self.client, timeout_seconds=45)

    def evaluate(self, question: Question, answer: str, mode: Mode) -> Evaluation:
        return self.evaluate_with_context(
            question, answer, mode, run_deterministic_checks(question, answer)
        )

    def evaluate_with_context(
        self,
        question: Question,
        answer: str,
        mode: Mode,
        deterministic: DeterministicReport,
    ) -> Evaluation:
        effort = (
            "high"
            if mode in {Mode.ASSESSMENT, Mode.MOCK_INTERVIEW}
            or question.difficulty >= 4
            else "medium"
        )
        self.transport.client = self.client or self.transport.client
        try:
            response = self.transport.parse(output_type=ReasoningEvaluation,
                instructions=PROMPT, context=_context(question, answer, mode, deterministic),
                run_id="evaluation:" + question.id, request_id=str(uuid.uuid4()),
                reasoning_effort=effort, max_output_tokens=1800)
        except (ProviderUnavailable, OSError) as exc:
            raise LLMUnavailable("OpenAI evaluation is temporarily unavailable or invalid") from exc
        return _to_evaluation(response.output, question=question, provider=self.name,
            model=response.model, deterministic=deterministic, response_id=response.response_id)


@dataclass
class QwenEvaluator:
    settings: Settings
    client: Any | None = None
    model: str = field(init=False)

    name: str = "qwen_local"

    def __post_init__(self) -> None:
        self.model = self.settings.qwen_model
        self.transport = ParsedModelClient("qwen_local", self.model,
            calling_system="toptal.evaluator", client=self.client,
            base_url=self.settings.qwen_base_url, timeout_seconds=self.settings.qwen_timeout_seconds)

    def health_check(self) -> tuple[bool, str | None]:
        healthy, reason = self.transport.health_check(self.settings.qwen_health_timeout_seconds)
        self.model = self.transport.model
        return healthy, reason

    def evaluate(self, question: Question, answer: str, mode: Mode) -> Evaluation:
        return self.evaluate_with_context(
            question, answer, mode, run_deterministic_checks(question, answer)
        )

    def evaluate_with_context(
        self,
        question: Question,
        answer: str,
        mode: Mode,
        deterministic: DeterministicReport,
    ) -> Evaluation:
        self.transport.client = self.client or self.transport.client
        try:
            response = self.transport.parse(output_type=ReasoningEvaluation,
                instructions=PROMPT, context=_context(question, answer, mode, deterministic),
                run_id="evaluation:" + question.id, request_id=str(uuid.uuid4()),
                max_output_tokens=2200)
        except (ProviderUnavailable, OSError) as exc:
            raise LLMUnavailable("Local Qwen unavailable or invalid structured JSON") from exc
        return _to_evaluation(response.output, question=question, provider=self.name,
            model=response.model, deterministic=deterministic, response_id=response.response_id)


@dataclass
class FailoverEvaluator:
    providers: tuple[EvaluationProvider, ...]

    @property
    def name(self) -> str:
        return " -> ".join(provider.name for provider in self.providers)

    def evaluate(self, question: Question, answer: str, mode: Mode) -> Evaluation:
        return self.evaluate_with_context(
            question, answer, mode, run_deterministic_checks(question, answer)
        )

    def evaluate_with_context(
        self,
        question: Question,
        answer: str,
        mode: Mode,
        deterministic: DeterministicReport,
    ) -> Evaluation:
        def invoke(provider):
            method = getattr(provider, "evaluate_with_context", None)
            return method(question, answer, mode, deterministic) if method else provider.evaluate(question, answer, mode)
        evaluation, failure = invoke_evaluators(self.providers, invoke, LLMUnavailable)
        return replace(evaluation, fallback_reason=failure) if failure else evaluation


@dataclass(frozen=True)
class ProviderSelection:
    provider: EvaluationProvider | None
    display_name: str
    fallback_reason: str | None = None


def select_provider(settings: Settings) -> ProviderSelection:
    providers, failures = select_evaluators(settings.evaluator_provider, settings.llm_mode,
        qwen_factory=lambda: QwenEvaluator(settings), openai_factory=lambda: OpenAIEvaluator(settings),
        unavailable_type=LLMUnavailable)
    if providers:
        provider = providers[0] if len(providers) == 1 else FailoverEvaluator(providers)
        return ProviderSelection(provider, provider.name,
            "; ".join(failures) if settings.evaluator_provider == "openai" and providers[0].name != "openai" and failures else None)
    return ProviderSelection(None, "offline fallback", "; ".join(failures) or "No reasoning evaluator configured")
