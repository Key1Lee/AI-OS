from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

POLICY_VERSION = "ae-v1"
LABELS = ["Unassessed", "Foundational Gap", "Developing", "Independent", "Senior Ready", "Strong Senior / Staff Signal"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def empty_state() -> dict:
    return dict(level=0, label=LABELS[0], confidence="none", attempts=0,
                successes=0, failures=0, assisted_successes=0,
                independent_successes=[], recent_attempts=[], highest_difficulty=0,
                last_tested=None, next_review=None, unresolved_mistakes=0,
                trend="unassessed", policy_version=POLICY_VERSION)


def advance(state: dict, evidence: dict, unresolved: int, now: datetime) -> dict:
    new = deepcopy(state)
    old_level = state["level"]
    new["attempts"] += 1
    new["last_tested"] = stamp(now)
    new["unresolved_mistakes"] = unresolved
    passed = evidence["passed"]
    independent = evidence["independent"] and passed
    prior = new["independent_successes"]
    cold = independent and bool(prior) and (now - parse(prior[-1]["at"])).total_seconds() >= 7 * 86400 and prior[-1]["exercise_id"] != evidence["exercise_id"]
    record = {**evidence, "at": stamp(now), "cold_transfer": cold}
    new["recent_attempts"] = (new["recent_attempts"] + [record])[-12:]
    if passed:
        new["successes"] += 1
        if independent and not any(e["exercise_id"] == evidence["exercise_id"] for e in prior):
            prior.append(record)
            new["highest_difficulty"] = max(new["highest_difficulty"], evidence["difficulty"])
        else:
            new["assisted_successes"] += 1
    else:
        new["failures"] += 1
    families = {e["family"] for e in prior}
    senior = sum(e["difficulty"] >= 4 for e in prior)
    expert = sum(e["difficulty"] >= 5 for e in prior)
    cold_count = sum(e.get("cold_transfer", False) for e in prior)
    level = 2 if new["successes"] else 1
    if len(prior) >= 2 and len(families) >= 2:
        level = 3
    if len(prior) >= 4 and len(families) >= 3 and senior >= 2 and cold_count >= 1:
        level = 4
    if len(prior) >= 6 and len(families) >= 4 and expert >= 2 and cold_count >= 2:
        level = 5
    if unresolved or not passed:
        level = min(level, 2)
    new["level"] = level
    new["label"] = LABELS[level]
    new["confidence"] = "strong" if len(prior) >= 6 else "moderate" if len(prior) >= 3 else "limited"
    new["trend"] = "improving" if level > old_level else "reopened" if level < old_level else "stable"
    interval = 30 if level >= 4 else 14 if cold else 7 if independent else 3 if passed else 1
    recent_failures = sum(not e["passed"] for e in new["recent_attempts"][-3:])
    if not passed and recent_failures >= 2:
        interval = 0.5
    new["next_review"] = stamp(now + timedelta(days=interval))
    new["policy_version"] = POLICY_VERSION
    return new
