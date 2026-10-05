"""Bounded probabilistic judgments; deterministic policy retains authority."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Callable, Mapping
from uuid import uuid4
from threading import Lock

from .budget import CloudCallBudget

_LABEL = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class DecisionQuestion:
    kind: str
    instructions: str
    criteria: tuple[str, ...] = ()
    version: str = "1"
    threshold: float = 0.8

    def validate(self) -> None:
        if self.kind not in {"choice", "score", "noul"}:
            raise ValueError("Decision provider accepts only choice, score, noul")
        if not self.instructions.strip() or not _LABEL.fullmatch(self.version):
            raise ValueError("Question needs instructions and criteria version")
        probability(self.threshold)
        if self.threshold <= 0.5:
            raise ValueError("Decision confidence threshold must exceed 0.5")
        if self.kind != "noul" and (not self.criteria or len(set(self.criteria)) != len(self.criteria)):
            raise ValueError("Choice/score criteria must be nonempty and distinct")
        if self.kind == "choice" and any(not _LABEL.fullmatch(x) for x in self.criteria):
            raise ValueError("Choice criteria must be safe labels")
        if self.kind == "noul" and self.criteria:
            raise ValueError("Noul does not accept a choice rubric")


@dataclass(frozen=True)
class DecisionRequest:
    calling_system: str
    run_id: str
    state: Mapping[str, Any]
    questions: Mapping[str, DecisionQuestion]
    private: bool = False
    offline: bool = False
    request_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class DecisionAnswer:
    kind: str
    selected: str | float
    probabilities: Mapping[str, float] = field(default_factory=dict)
    confidence: float | None = None


@dataclass(frozen=True)
class DecisionResult:
    request_id: str
    status: str
    branch: str
    provider: str | None = None
    model: str | None = None
    answers: Mapping[str, DecisionAnswer] = field(default_factory=dict)
    usage: Mapping[str, int] = field(default_factory=dict)
    latency_ms: int | None = None
    error: str | None = None
    verification_metadata: Mapping[str, Any] = field(default_factory=dict)


def probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Probability must be finite and within [0,1]")
    return float(value)


def validate_answers(questions: Mapping[str, DecisionQuestion], answers: Mapping[str, DecisionAnswer]) -> None:
    if set(questions) != set(answers):
        raise ValueError("Decision response question set mismatch")
    for name, question in questions.items():
        answer = answers[name]
        if answer.kind != question.kind:
            raise ValueError("Decision response type mismatch")
        if question.kind == "noul":
            probability(answer.selected)
            if answer.probabilities or answer.confidence is not None:
                raise ValueError("Noul is a yes probability, not a confidence score")
            continue
        probability(answer.confidence)
        expected = set(question.criteria) if question.kind == "choice" else {str(i) for i in range(len(question.criteria))}
        if set(answer.probabilities) != expected:
            raise ValueError("Decision probability rubric mismatch")
        values = {key: probability(value) for key, value in answer.probabilities.items()}
        if not math.isclose(sum(values.values()), 1, abs_tol=0.02):
            raise ValueError("Decision distribution is not normalized")
        if question.kind == "choice":
            if answer.selected not in expected or values[answer.selected] < max(values.values()) - 1e-6:
                raise ValueError("Selected choice contradicts distribution")
        else:
            score = answer.selected
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= len(question.criteria) - 1:
                raise ValueError("Score outside bounded rubric")
            expected_score = sum(int(key) * value for key, value in values.items())
            if not math.isclose(score, expected_score, abs_tol=0.05):
                raise ValueError("Score contradicts probability-weighted rubric")


class DecisionService:
    """No generative fallback. A failed invariant is irreversible within this call.

    The workflow owns the branch policy. Probability never grants security rights.
    The default branch is REVIEW: a judgment alone cannot authorize an action.
    """
    def __init__(self, provider=None, *, enabled: bool = False, budget: CloudCallBudget | None = None,
                 audit_sink: Callable[[Mapping[str, Any]], None] | None = None, per_run_calls: int = 1):
        if isinstance(per_run_calls, bool) or not isinstance(per_run_calls, int) or per_run_calls < 0:
            raise ValueError("Per-run decision limit must be nonnegative")
        self.provider = provider
        self.enabled = enabled
        self.budget = budget or CloudCallBudget(0)
        from .telemetry import EventSink
        self.audit_sink = audit_sink or EventSink()
        self.per_run_calls = per_run_calls
        self.used_by_run: dict[tuple[str, str], int] = {}
        self._budget_lock = Lock()

    @classmethod
    def from_env(cls):
        from .decision_config import DecisionSettings
        from .providers.jev import JevProvider
        settings = DecisionSettings.from_env()
        return cls(JevProvider(settings.model), enabled=settings.enabled,
                   budget=CloudCallBudget(settings.daily_calls, settings.budget_file), per_run_calls=settings.per_run_calls)

    def decide(self, request: DecisionRequest, *, deterministic_checks: Mapping[str, bool | None] | None = None,
               policy: Callable[[Mapping[str, DecisionAnswer]], str] | None = None,
               high_risk: bool = False, human_approved: bool = False) -> DecisionResult:
        if any(not _LABEL.fullmatch(x) for x in (request.calling_system, request.run_id, request.request_id)):
            raise ValueError("Decision attribution must use safe identifiers")
        checks = dict(deterministic_checks or {})
        if any(value is not None and not isinstance(value, bool) for value in checks.values()):
            raise ValueError("Deterministic checks are bool or unresolved None")
        if any(value is False for value in checks.values()):
            return self._record(request, DecisionResult(request.request_id, "REJECTED", "DENY", verification_metadata={"deterministic": "failed"}))
        if high_risk and not human_approved:
            return self._record(request, DecisionResult(request.request_id, "REVIEW", "REVIEW", verification_metadata={"human_approval": "required"}))
        if checks and all(value is True for value in checks.values()):
            return self._record(request, DecisionResult(request.request_id, "VERIFIED", "ALLOW", verification_metadata={"deterministic": "passed"}))
        if not request.questions:
            return self._record(request, DecisionResult(request.request_id, "REVIEW", "REVIEW", error="No bounded question or deterministic verdict"))
        for name, question in request.questions.items():
            if not _LABEL.fullmatch(name):
                raise ValueError("Question name must be a safe identifier")
            question.validate()
        if request.private or request.offline or not self.enabled or self.provider is None:
            return self._record(request, DecisionResult(request.request_id, "UNAVAILABLE", "REVIEW", error="Decision provider prohibited or disabled"))
        try:
            run_key = (request.calling_system, request.run_id)
            if not self.provider.available() or not self._reserve(run_key):
                return self._record(request, DecisionResult(request.request_id, "UNAVAILABLE", "REVIEW", error="Decision provider unavailable or budget exhausted"))
            result = self.provider.evaluate(request)
            validate_answers(request.questions, result.answers)
            uncertain = any((answer.confidence < request.questions[name].threshold if answer.kind != "noul"
                             else 1 - request.questions[name].threshold < answer.selected < request.questions[name].threshold)
                            for name, answer in result.answers.items())
            branch = "REVIEW" if uncertain or policy is None else policy(result.answers)
            if branch not in {"ALLOW", "REVIEW", "DENY"}:
                raise ValueError("Invalid workflow decision branch")
            result = DecisionResult(request.request_id, "JUDGED", branch, "jev", result.model, result.answers,
                                    result.usage, result.latency_ms, verification_metadata={"probabilistic": True, "deterministic": "unresolved"})
        except Exception:
            result = DecisionResult(request.request_id, "UNAVAILABLE", "REVIEW", provider="jev", error="Decision call or validation failed")
        return self._record(request, result)

    def _reserve(self, run_key: tuple[str, str]) -> bool:
        with self._budget_lock:
            if self.used_by_run.get(run_key, 0) >= self.per_run_calls or not self.budget.reserve():
                return False
            self.used_by_run[run_key] = self.used_by_run.get(run_key, 0) + 1
            return True

    def _record(self, request: DecisionRequest, result: DecisionResult) -> DecisionResult:
        # Whitelisted metadata only. Never record state or question instructions.
        event = {"request_id": request.request_id, "calling_system": request.calling_system, "run_id": request.run_id,
                 "capability": "bounded_decision", "provider": result.provider, "model": result.model,
                 "status": result.status, "latency_ms": result.latency_ms, "usage": dict(result.usage),
                 "branch": result.branch, "verification": dict(result.verification_metadata), "fallback": False,
                 "questions": {name: {"type": question.kind, "version": question.version, "criteria": list(question.criteria),
                                       "threshold": question.threshold,
                                       "answer": asdict(result.answers[name]) if name in result.answers else None}
                               for name, question in request.questions.items()}}
        try:
            self.audit_sink(event)
        except Exception:
            return DecisionResult(request.request_id, "UNAVAILABLE", "REVIEW", error="Decision audit unavailable")
        return result
