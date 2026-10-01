from __future__ import annotations

from datetime import datetime

from trainer.exercises.bank import Bank
from trainer.mastery.policy import parse


def readiness(history: list[dict]) -> int:
    recent = history[-5:]
    if sum(h["result"]["outcome"] != "Correct" for h in recent[-3:]) >= 2:
        return 2
    independent = [h for h in recent if h["result"].get("independent")]
    if len(independent) >= 2:
        return min(6, max(3, min(h["difficulty"] for h in independent[-2:]) + 1))
    return 3


def recommend(bank: Bank, mastery: dict[str, dict], history: list[dict], now: datetime, *, competency=None, difficulty=None, practice=False) -> dict | None:
    ready = readiness(history)
    scores = []
    for exercise in bank.exercises.values():
        if competency and competency not in exercise.competencies:
            continue
        if difficulty and difficulty != exercise.difficulty:
            continue
        requirements = set(exercise.prerequisites)
        for key in exercise.competencies:
            requirements.update(bank.competencies[key].prerequisites)
        missing = [p for p in requirements if p not in exercise.competencies and mastery[p]["level"] < 2]
        if not practice and (exercise.difficulty > ready or missing):
            continue
        states = [mastery[key] for key in exercise.competencies]
        previous = [h for h in history if h["exercise_id"] == exercise.id]
        recent = history[-3:]
        failing_families = {e["family"] for s in states for e in s["recent_attempts"][-3:] if not e["passed"]}
        factors = {
            "weakness": sum(1 if s["level"] == 1 else 0.5 if s["level"] == 2 else 0 for s in states) / len(states),
            "review_due": sum(bool(s["next_review"] and parse(s["next_review"]) <= now) for s in states) / len(states),
            "importance": sum(bank.competencies[k].importance for k in exercise.competencies) / (5 * len(states)),
            "difficulty_match": 1 if exercise.difficulty == ready else 0.5 if exercise.difficulty < ready else 0,
            "coverage_gap": sum(s["attempts"] == 0 for s in states) / len(states),
            "misconception": sum(s["unresolved_mistakes"] > 0 for s in states) / len(states),
            "transfer": 1 if failing_families and exercise.family not in failing_families and not previous else 0,
            "repetition": 1 if any(h["exercise_id"] == exercise.id for h in recent) else 0.5 if previous else 0,
            "overpractice": min(3, len(previous)) / 3,
        }
        weighted = {key: round(value * bank.weights[key] * (-1 if key in {"repetition", "overpractice"} else 1), 2) for key, value in factors.items()}
        reasons = []
        if factors["transfer"]: reasons.append("A different context retests a recent gap.")
        if factors["review_due"]: reasons.append("Related competencies are due for review.")
        if factors["misconception"]: reasons.append("Targets an unresolved test failure.")
        if factors["coverage_gap"]: reasons.append("Adds evidence in unassessed competencies.")
        if not reasons: reasons.append("Matches your current demonstrated difficulty.")
        scores.append(dict(exercise_id=exercise.id,title=exercise.title,difficulty=exercise.difficulty,priority=round(sum(weighted.values()),2),factors=weighted,reasons=reasons,readiness=ready,practice_only=bool(previous),missing_prerequisites=missing))
    scores.sort(key=lambda s: (-s["priority"], s["exercise_id"]))
    return scores[0] if scores else None
