from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
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
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if self.client is None:
            if not key:
                raise LLMUnavailable("OPENAI_API_KEY is not set")
            self.client = OpenAI(api_key=key, timeout=45.0, max_retries=0)

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
        try:
            response = self.client.responses.parse(
                model=self.settings.model,
                instructions=PROMPT,
                input=json.dumps(
                    _context(question, answer, mode, deterministic), ensure_ascii=False
                ),
                reasoning={"effort": effort},
                text_format=ReasoningEvaluation,
                max_output_tokens=1800,
                store=False,
            )
        except (APITimeoutError, RateLimitError, APIConnectionError, APIError) as exc:
            raise LLMUnavailable("OpenAI evaluation is temporarily unavailable") from exc
        except Exception as exc:
            raise LLMUnavailable("OpenAI returned an invalid structured evaluation") from exc
        parsed = response.output_parsed
        if parsed is None:
            raise LLMUnavailable("OpenAI returned no structured evaluation")
        return _to_evaluation(
            parsed,
            question=question,
            provider=self.name,
            model=self.settings.model,
            deterministic=deterministic,
            response_id=getattr(response, "id", None),
        )


@dataclass
class QwenEvaluator:
    settings: Settings
    client: Any | None = None
    model: str = field(init=False)

    name: str = "qwen_local"

    def __post_init__(self) -> None:
        self.model = self.settings.qwen_model
        if self.client is None:
            self.client = OpenAI(
                api_key=self.settings.qwen_api_key,
                base_url=self.settings.qwen_base_url,
                timeout=self.settings.qwen_timeout_seconds,
                max_retries=0,
            )

    def health_check(self) -> tuple[bool, str | None]:
        try:
            models = list(
                self.client.models.list(
                    timeout=self.settings.qwen_health_timeout_seconds
                ).data
            )
        except (APITimeoutError, APIConnectionError, APIError) as exc:
            return False, f"Qwen health check failed: {type(exc).__name__}"
        except Exception as exc:
            return False, f"Qwen health check failed: {type(exc).__name__}"
        if not models:
            return False, "Qwen endpoint returned no models"
        if not self.model:
            ids = [str(item.id) for item in models]
            self.model = next((item for item in ids if "qwen" in item.casefold()), ids[0])
        return True, None

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
        payload = _context(question, answer, mode, deterministic)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=2200,
            )
        except (APITimeoutError, RateLimitError, APIConnectionError, APIError) as exc:
            raise LLMUnavailable("Local Qwen evaluation is unavailable") from exc
        except Exception as exc:
            raise LLMUnavailable("Local Qwen evaluation failed") from exc
        content = response.choices[0].message.content if response.choices else None
        if not isinstance(content, str) or not content.strip():
            raise LLMUnavailable("Local Qwen returned no evaluation JSON")
        try:
            parsed = ReasoningEvaluation.model_validate_json(content)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise LLMUnavailable("Local Qwen returned invalid structured JSON") from exc
        return _to_evaluation(
            parsed,
            question=question,
            provider=self.name,
            model=self.model,
            deterministic=deterministic,
            response_id=getattr(response, "id", None),
        )


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
        failures: list[str] = []
        for provider in self.providers:
            try:
                method = getattr(provider, "evaluate_with_context", None)
                evaluation = (
                    method(question, answer, mode, deterministic)
                    if method
                    else provider.evaluate(question, answer, mode)
                )
                if failures:
                    evaluation = replace(
                        evaluation, fallback_reason="; ".join(failures)
                    )
                return evaluation
            except LLMUnavailable as exc:
                failures.append(f"{provider.name}: {exc}")
        raise LLMUnavailable("; ".join(failures) or "No reasoning evaluator available")


@dataclass(frozen=True)
class ProviderSelection:
    provider: EvaluationProvider | None
    display_name: str
    fallback_reason: str | None = None


def select_provider(settings: Settings) -> ProviderSelection:
    requested = settings.evaluator_provider
    if settings.llm_mode == "off" and requested == "auto":
        requested = "offline_fallback"
    if requested == "offline_fallback":
        return ProviderSelection(None, "offline fallback", "explicitly configured")

    providers: list[EvaluationProvider] = []
    failures: list[str] = []
    if requested == "openai":
        try:
            providers.append(OpenAIEvaluator(settings))
        except LLMUnavailable as exc:
            failures.append(str(exc))

    if requested in {"auto", "qwen_local", "openai"}:
        qwen = QwenEvaluator(settings)
        healthy, reason = qwen.health_check()
        if healthy:
            providers.append(qwen)
        else:
            failures.append(reason or "Qwen endpoint unhealthy")

    if providers:
        provider: EvaluationProvider = (
            providers[0]
            if len(providers) == 1
            else FailoverEvaluator(tuple(providers))
        )
        return ProviderSelection(
            provider,
            provider.name,
            (
                "; ".join(failures)
                if requested == "openai"
                and providers[0].name != "openai"
                and failures
                else None
            ),
        )
    if settings.llm_mode == "required":
        raise LLMUnavailable("; ".join(failures) or "Required evaluator unavailable")
    return ProviderSelection(
        None,
        "offline fallback",
        "; ".join(failures) or "No reasoning evaluator configured",
    )
