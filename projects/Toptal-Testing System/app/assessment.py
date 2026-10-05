from __future__ import annotations


CANONICAL_COMPETENCIES = (
    "Requirements clarification, discovery, ambiguous problem decomposition",
    "SQL, relational reasoning, data modeling, query performance",
    "Python, implementation, algorithms and data structures where relevant",
    "APIs, HTTP, SaaS integrations, brownfield interoperability",
    "Authentication, authorization, security, least privilege",
    "ETL/ELT, dbt, data pipelines, cross-system reconciliation",
    "Git and safe engineering changes",
    "Cloud fundamentals, deployment, rollout, handoff and adoption",
    "Deterministic automation, n8n and workflow orchestration",
    "Testing, verification and regression analysis",
    "Debugging and production troubleshooting",
    "Reliability, retries, idempotency, observability and recovery",
    "System design, architectural defense, scalability and cost",
    "AI/LLM integration, necessity, evaluation and failure handling",
    "Stakeholder communication, prioritization and measurable business outcomes",
)


MODULES = (
    "Module 1 — Customer discovery and problem decomposition",
    "Module 2 — SQL, data reasoning and data modeling",
    "Module 3 — Python and software engineering",
    "Module 4 — API and enterprise integration",
    "Module 5 — System design",
    "Module 6 — Production debugging",
    "Module 7 — Reliability and failure engineering",
    "Module 8 — AI / LLM system design",
    "Module 9 — AI evaluation",
    "Module 10 — Security and permissions",
    "Module 11 — Observability and operations",
    "Module 12 — Stakeholder communication",
    "Module 13 — Prioritization and delivery",
    "Module 14 — Architecture defense",
    "Module 15 — Complete forward-deployed project",
)


def next_module(current: str) -> str | None:
    try:
        index = MODULES.index(current)
    except ValueError:
        return None
    if index + 1 >= len(MODULES):
        return None
    return MODULES[index + 1]

