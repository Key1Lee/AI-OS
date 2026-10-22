# Additive working slice

Source: the original SQLite simulation and the Python 3.12 interview foundation.
Target: an independent, completed policy assistant in `policy_assistant/`, using
the foundation's Python/FastAPI/PostgreSQL patterns. The learner's exercises,
training database, and original API contracts remain unchanged.

Sequence: build and run one PTO ingestion → authenticated retrieval → citation
test first; extend policy/security cases; add n8n and chat; run the entire slice.
The new Compose project is `peopleops-policy`, database `peopleops_policy`, API
port 8810, database port 55433, n8n port 5680. The test database is separate.

Version/content hashes and tenant locking protect duplicate ingestion. Current
version selection precedes ACL filtering, preventing old ACLs from resurrecting
retired evidence. Vector spaces are labeled, so provider changes require
re-ingesting identical sources to create new embeddings, not rewriting history.

Recovery: stop this Compose project without deleting its volumes. Existing apps
are still runnable. Schema v1 is additive initialization only; later destructive
schema changes need explicit migrations and backups. Nothing here is deployed
to production, and assistant-authored implementation is not learner mastery.

## Local provider transition · 2026-10-20

Source: mock evidence selector. Target: installed Qwen3-4B-Q4_K_M via the existing
AI-OS llama.cpp server on the Mac, plus the n8n Assistant's saved local-model
connection. There is no new model download, database migration, or vector-space
change: embeddings remain the offline mock. Qwen returns schema-constrained IDs;
the same deterministic authorization and citation checks still apply.

Sequence: discover and check existing runtime; prove Docker-to-Mac connectivity;
add a local-only provider profile; recreate API; run mock regressions and live
workflow cases; connect and reload-check the n8n Assistant model setting.
Rollback: choose `LLM_PROVIDER=mock` and recreate API; model settings in n8n are
independent and can be changed through its Model dialog. No documents need deletion.

## Enterprise reference transition · 2026-10-20

Source state: the working pgvector/n8n/Qwen policy assistant and separate training
lab. Target state: an additional deterministic SQLite enterprise reference at
`app.main:app` on 8811, as requested by the latest master prompt. This is an
additive entrypoint; it does not convert or reuse the PostgreSQL or n8n volumes.

Invariants: learner exercises, the existing `app.api` contracts, Qwen runtime,
and stored policy/n8n state are preserved. All new records are synthetic.
The newer mock permits only explicitly authorized self/delegated PTO reads;
that does not add record tools to the earlier policy-only app.

Sequence completed: requirements and criteria, fixtures, isolated ingestion,
identity/ACLs, routing and read-only tools, response checks, tests, independent
evaluations, portal QA and CI configuration. Evidence is in
`enterprise-verification.md`. SQLite initialization is an additive local schema
initializer, not a production migration engine.

Compatibility/recovery: use the earlier launcher for the existing stack, or
stop 8811 and retain its SQLite file. A fresh reference index can be rebuilt
from the governed fixtures at a new HR_DATABASE_PATH. Back up before intentional
data changes; do not undo a revocation by restoring an older public index.
No destructive cutover or production release was performed.

## Interactive lab transition · 2026-10-20

Source: enterprise 2.0 portal with string traces and JSON-backed mock sources.
Target: additive 2.1 layer with structured measured traces, YAML rule configuration,
SQLite identity/Workday source tables, request-scoped failures and allowlisted
subprocess jobs. Existing response fields remain; new diagnostics are additive.
Duplicate receipts preserve business facts/citations/status/correlation, while
per-request diagnostics now distinguish a replay from a fresh protected read.
Receipt authority snapshots prevent restored access after grants/inventory change.

The existing SQLite file was backed up before expansion. New source tables and
seed digests are additive; the existing index, audits, receipts, PostgreSQL and
n8n volumes are preserved. JSON fixture data is the reproducible seed rather
than the runtime employee-record authority. The plan and recovery boundary are
in `testing-layer-plan.md`; execution evidence is in `testing-layer-verification.md`.
