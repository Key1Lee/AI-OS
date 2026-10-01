from __future__ import annotations

import hashlib
from dataclasses import replace

from .models import Question


DOMAINS = (
    "healthcare scheduling",
    "B2B payments",
    "logistics tracking",
    "industrial telemetry",
    "public-sector case management",
    "retail inventory",
)
CONSTRAINTS = (
    "the team has 48 hours for a safe first increment",
    "the service must remain available during rollout",
    "auditability is a contractual requirement",
    "traffic is expected to triple within a quarter",
    "the partner contract cannot change this month",
    "two application versions will coexist during deployment",
)


def originalize(question: Question, session_id: int, exposure: int) -> Question:
    """Create a reproducible scenario combination without changing its rubric contract."""
    digest = hashlib.sha256(f"{question.id}:{session_id}:{exposure}".encode()).digest()
    domain = DOMAINS[digest[0] % len(DOMAINS)]
    constraint = CONSTRAINTS[digest[1] % len(CONSTRAINTS)]
    context = f"Scenario: You are the senior engineer for a {domain} system; {constraint}."
    family = f"{question.family}:{domain}"
    difficulty = min(5, question.difficulty + exposure // 2)
    return replace(
        question,
        family=family,
        difficulty=difficulty,
        prompt=f"{context}\n\n{question.prompt}",
    )
