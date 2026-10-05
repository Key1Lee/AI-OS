"""Official TypeSafe SDK transport for bounded System One questions only."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
import time
from typing import Any

from ..decisions import DecisionAnswer, DecisionRequest, DecisionResult, validate_answers
from .base import ProviderUnavailable, usage_dict


@dataclass
class JevProvider:
    model: str
    client: Any = None
    name: str = "jev"

    def available(self) -> bool:
        return bool(self.model and (self.client is not None or (os.getenv("TYPESAFE_API_KEY") and importlib.util.find_spec("typesafe_sdk"))))

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        for question in request.questions.values():
            question.validate()
        if not self.available():
            raise ProviderUnavailable("Jev SDK, credential or model missing")
        owned = self.client is None
        started = time.monotonic()
        client = self.client
        try:
            if owned:
                from typesafe_sdk import TypeSafeClient, RetryPolicy
                client = TypeSafeClient(model=self.model, timeout=30, retry=RetryPolicy(max_retries=0))
            # Raw question dictionaries are an official public SDK input, not a recreated wire client.
            questions = {name: {"type": q.kind, "instructions": q.instructions,
                               **({"criteria": {label: None for label in q.criteria}} if q.kind == "choice"
                                  else {"criteria": list(q.criteria)} if q.kind == "score" else {})}
                         for name, q in request.questions.items()}
            response = client.system_one(state=dict(request.state), questions=questions, model=self.model, timeout=30)
            answers = {}
            if set(response.answers) != set(questions):
                raise ValueError("Jev returned an unexpected question set")
            for name, q in request.questions.items():
                raw = response.answers[name]
                if raw.type != q.kind:
                    raise ValueError("Jev answer type mismatch")
                if q.kind == "noul":
                    answers[name] = DecisionAnswer(q.kind, raw.noul)
                else:
                    if q.kind == "score" and {str(k): v for k, v in raw.legend.items()} != {str(i): v for i, v in enumerate(q.criteria)}:
                        raise ValueError("Jev changed the score legend")
                    answers[name] = DecisionAnswer(q.kind, raw.choice if q.kind == "choice" else raw.score,
                                                   {str(k): v for k, v in raw.probabilities.items()}, raw.confidence)
            if response.model != self.model:
                raise ValueError("Jev returned an unrequested model; use a pinned model identifier")
            validate_answers(request.questions, answers)
            return DecisionResult(request.request_id, "JUDGED", "REVIEW", self.name, response.model, answers,
                                  usage_dict(response.usage), int((time.monotonic() - started) * 1000))
        except Exception as exc:
            raise ProviderUnavailable("Jev transport or response validation failed") from None
        finally:
            if owned and client is not None:
                client.close()
