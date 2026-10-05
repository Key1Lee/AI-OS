"""Consumer adapter for the existing Toptal deterministic evaluation contract."""
from __future__ import annotations

from lab.adapters.bridge import invoke


class NativeTestingAdapter:
    def evaluate(self, stage: str, answer: dict) -> dict:
        if stage not in {"predict", "diagnose", "recall"}:
            raise ValueError("Choose predict, diagnose or recall for learner evaluation.")
        if not isinstance(answer, dict):
            raise ValueError("Learner answers must be a structured object.")
        return invoke("testing", {"stage": stage, "answer": answer})
