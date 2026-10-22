"""Authoring metadata, never exercise answers."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS = [
    ("E01", 1, "Normalize one employee", "e01_cleaning.py", "Workday sends Maya's name with extra spaces and an uppercase email. Produce one validated record without mutating the source.", "Dictionary access, pure functions, validation, date parsing.", "Explain whether an invalid row should reject a batch or enter quarantine."),
    ("E02", 1, "Deduplicate recruiting deliveries", "e02_duplicates.py", "EVT-0001 arrives twice, and the older delivery is last. Keep the newest source version per event ID.", "Hash maps, aware timestamps, deterministic tie-breaking.", "Explain replay safety and why arrival order is not source version order."),
    ("E03", 1, "Write HR metric queries", "e03_analytics.sql", "Start with current headcount per department; then turnover, funnel, and onboarding. Preserve the documented grain across joins.", "GROUP BY, conditional aggregation, distinct grains, LEFT JOIN, zero denominators.", "Explain which join can multiply the denominator and how to detect it."),
    ("E04", 2, "Chunk policy sections", "e04_chunking.py", "A policy has two sections and a version. Split long sections without losing the exact citation location.", "Iteration, stable IDs, boundaries, provenance.", "Explain why mixing versions or sections creates misleading citations."),
    ("E05", 2, "Retrieve authorized evidence", "e05_retrieval.py", "PTO v1 promises 120 hours; current v2 promises 160. Rank only current, permitted policy chunks in PostgreSQL.", "SQLAlchemy joins, cosine distance, filter-before-top-k.", "Explain why filtering after retrieval changes both privacy and recall."),
    ("E06", 2, "Ground answers and refuse", "e06_grounding.py", "A payroll answer needs an exact section and version. Unsupported or malicious requests must not become invented policy.", "Typed output validation, evidence checks, uncertainty, prompt/data boundaries.", "Explain a failure that keyword injection detection cannot prevent."),
    ("E07", 3, "Authorize one operation", "e07_authorization.py", "Maya can read her own PTO. A manager role alone does not grant access to all employee records.", "Deny by default, role scope, resource ownership.", "Explain why a client-provided role or owner field cannot be trusted."),
    ("E08", 3, "Implement employee and recruiting endpoints", "e08_endpoints.py", "Expose employee details, job openings, candidate records, and aggregate metrics using the security matrix.", "FastAPI dependencies, response models, parameter binding, HTTP errors.", "Explain authorization before existence disclosure and response-field minimization."),
    ("E09", 4, "Plan a safe tool call", "e09_planning.py", "Employee needs help with payroll. Prepare a Payroll ticket plan; ambiguous PTO dates require clarification.", "Allowlisted tools, structured arguments, validation, plan versus execution.", "Explain why a model's selected tool is not permission to execute it."),
    ("E10", 4, "Confirm and execute exactly once locally", "e10_actions.py", "A double click must create one request. Bind confirmation to the actor, immutable proposal, expiry, and idempotency key.", "Transactions, locks, unique constraints, payload hashing, explicit confirmation.", "Explain the crash-after-external-send boundary and why this local guarantee differs."),
    ("E11", 5, "Recover paginated source reads", "e11_reliability.py", "Page two times out twice before succeeding. Retry that page without losing or duplicating page one.", "Bounded backoff, retry classification, cursor cycles, contract validation.", "Explain retry storms, time budgets, and which failures must not be retried."),
    ("E12", 5, "Ingest a batch atomically", "e12_ingestion.py", "An update and a malformed employee arrive together. Preserve prior data when validation or database work fails.", "Unit of work, source versions, upserts, rollback boundaries.", "Explain recovery after process death and handling partial source snapshots."),
    ("E13", 4, "Read prior request status", "e13_status.py", "Maya asks about TKT-001. Other employees must receive the same response for missing and unauthorized IDs.", "Ownership checks, resource types, safe output schemas.", "Explain how enumeration leaks information even without returning a record."),
]
rows = []
for code, phase, title, filename, problem, concepts, implications in LESSONS:
    test_file = "test_e03_analytics.py" if code == "E03" else "test_" + filename
    rows.append({"id": code, "phase": phase, "title": title, "file": "exercises/" + filename,
                 "test": "uv run pytest tests/exercises/" + test_file,
                 "problem": problem, "concepts": concepts, "production_question": implications})
(ROOT / "fixtures" / "curriculum.json").write_text(json.dumps(rows, indent=2) + "\n")
