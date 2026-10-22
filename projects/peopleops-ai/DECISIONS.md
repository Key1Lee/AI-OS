# PeopleOps architecture and teaching decisions

Updated: 2026-10-18. Existing system detail and original alternatives remain in
[training architecture](training/docs/architecture.md). This is the evolving
decision record; implementation status is explicit.

| ID | Decision / status | Reason | Alternative rejected / revisit trigger |
| --- | --- | --- | --- |
| D01 | Preserve original demo; use isolated training environment — implemented | Protect working data and keep solved reference code out of learner exercises | Rebuilding the project would discard working infrastructure; revisit retirement only when requested |
| D02 | Modular synchronous Python, PostgreSQL/pgvector, one API — implemented foundation | Makes contracts, SQL, and transactions inspectable with few moving parts | Microservices/distributed workers before measured scale add unnecessary failure modes |
| D03 | Seed 42, fixed business date 2026-10-01, locked packages/base images — implemented | Reproduce examples and failures independently of current time | Random/live enterprise data would make debugging unsafe and irreproducible |
| D04 | Business functions remain incomplete; one active task — enforced | Independent implementation is the learning outcome | Completing all features with generated code obscures the learner's actual ability |
| D05 | Shared provider call interface for fake/optional real transports — plumbing implemented | Keep provider selection separate from evidence and permission decisions | Separate fake-only business flow would invalidate later parity checks; orchestration remains E06/E09 work |
| D06 | Backend permission checks, authorized retrieval, immutable confirmed actions — designed, not implemented | Model output cannot grant access or authorize a write | Prompt-only authorization is insufficient; enforce and test these in E05–E10 |
| D07 | Local synthetic single-tenant environment — current limit | Existing schema/principal has no tenant key; do not claim cross-tenant isolation | Silent multi-tenancy without keys/constraints is unacceptable; design explicit tenant propagation before multi-tenant exercises |
| D08 | Separate infrastructure evidence, exercise completion, and mastery — adopted Level 2 | A copied or assisted pass does not demonstrate independent skill | A single progress percentage hides gaps; require independent variation plus explanation |
| D09 | Six-category 10-point rubric and recorded assistance 0–5 — adopted Level 2 | Tracks implementation quality and independence separately | Earlier five-category rubric did not explicitly score independence; superseded without inventing prior scores |
| D10 | Isolated deterministic DEBUG scenarios — required for future fault exercises | Keep a working baseline and allow causal investigation | Global outages during a learner exercise obscure causes and disrupt unrelated work |
| D11 | Reuse six repository state files as the session record — adopted Level 2 | Makes current task and evidence inspectable without a new tracking framework | Database-backed assessment service is unnecessary for this stage |

## Level 2 gaps scheduled by milestone

These are accepted requirements with pending implementation, not completed
security or chaos features. Do not implement them all before the first exercise.

| Requirement | Present evidence | Next appropriate milestone |
| --- | --- | --- |
| Tenant/user isolation | Authentication principal exists; no tenant dimension; business authorization stubs | Phase 3 design and negative tests before exposing multi-tenant records |
| Authorized retrieval before prompt construction | Shared provider transport exists; E05/E06 pending | Phase 2 implementation and hostile-document evaluation |
| Forged identities | Existing foundation tests reject invented tokens and X-Role overrides | Retain regression; add tenant/record threats in Phase 3 |
| Unauthorized salary/candidate lookups | Candidate authorization tests pending; no salary field/endpoint in training model | Phase 3 isolated synthetic threat cases; never introduce real salary data |
| Exact-payload confirmation and replay | Proposal/receipt schema and UI exist; E10 pending | Phase 4 backend permission, expiry, hash and concurrent replay checks |
| Durable redacted action audit | Schema exists; HTTP metadata redaction tests pass; action audit pending | Phase 4 transactional action implementation |
| Named fault profiles with logs, seed, trigger, recovery, regression, RCA | Existing mock scenarios/fixtures cover parts; complete scenario packaging is pending | Isolated cases at the associated learning milestone |

Current mock scenarios include normal, duplicate, timeout, intermittent,
unavailable, missing, malformed, and schema_drift. Out-of-order raw event copies
and retired PTO policy data exist. A complete `OUT_OF_ORDER_EVENTS`,
`PARTIAL_FAILURE`, `DATABASE_UNAVAILABLE`, `STALE_POLICY`, or
`UNAUTHORIZED_ACCESS` training profile with its full evidence packet must not
be described as implemented yet. Each future DEBUG packet needs reproducible
seed/trigger, observed and expected behavior, logs, files, regression command,
and a learner hypothesis field. Withhold the diagnosis until investigation.

## Staff design review gate

After a significant implemented milestone, ask the learner to propose a design
for a hypothetical 50,000-person organization with regional policies and near-real-time
recruiting data. Require architecture, data flow, storage/indexing, authorization,
reliability, observability, cost/latency, evaluation, rollout, and rollback.
Review against measured constraints and a rejected alternative; do not reward
speculative infrastructure. This review is prepared, not assigned now.

## D12 · Completed policy assistant, separate from the curriculum (2026-10-19)

The user explicitly requested a working FastAPI/pgvector/n8n application with
no questions. Implement it in `policy_assistant/`, using the existing foundation
patterns without overwriting learner exercises or either existing database.
Use immutable Markdown versions, materialized SQL ACL filtering before vector
ranking, exact excerpt answers selected by a configurable provider, and local
generated bearer identities. Default mock providers keep development free of
paid keys; genuine semantic embeddings are an explicit configuration choice.
The app is production-inspired, not a production deployment or evidence of
learner mastery. See `policy_assistant/docs/transition.md` for boundaries and
`policy_assistant/docs/verification.md` for executed checks.

## D13 · Installed Qwen as the local provider (2026-10-20)

The user requested the downloaded Qwen as the connected provider on their Mac.
The existing AI-OS runtime serves Qwen3-4B-Q4_K_M on loopback port 8080; Docker
reaches it through host.docker.internal. The working app's qwen_local profile
restricts endpoint hosts, disables selection-task thinking, requests a strict
JSON schema, and retains deterministic ACL and citation validation. Cloud access
is disabled. The embedding space stays mock; no reindex is needed.
The launcher reuses/starts the existing shared runtime rather than downloading
or copying a model. n8n Assistant's local model setting was also connected and
reload-verified; code sandbox and web search were left unset. This is application
configuration, not learner mastery. Evidence: policy_assistant/docs/verification.md.

## D14 · Standalone enterprise reference (2026-10-20)

The latest attached master prompt chooses a free, deterministic SQLite mock.
Implement it additively as `policy_assistant/app/main.py` on 8811 with its own
database; retain `app.api`/PostgreSQL/n8n/Qwen on 8810. Synthetic PTO can be read
only after self-service or explicit target-scoped delegation checks. Slack HMAC
and enterprise session authentication remain separate; the router and any future
LLM cannot grant access or generate numeric source facts.

Use an independently governed inventory, current version selection before ACLs,
content-digest verification, exact excerpts and fail-closed conflicts. Requirements
map to executed tests and independent labels, with source fingerprints preventing
stale local test evidence from satisfying release gates. Public fixture identity
switching is a deliberate local demo feature, disabled with HR_DEMO_MODE=false.
No real Slack/Workday data or production deployment is authorized by this work.
See the enterprise guide, readiness assessment and verification report in
`policy_assistant/docs/`. Training and interview checkpoints remain pending.

## D15 · Interactive engineering layer (2026-10-20)

Extend the same enterprise portal rather than create another application.
Measure real executed stages and return only authorized source metadata and
actual configured rule matches. Runtime synthetic identity/PTO authority is
SQLite; JSON remains an idempotent seed. Preserve exact balances, explicit
delegation and separate Slack/session verification. Receipt reuse binds the
current authority and inventory snapshot, with fresh replay diagnostics.

Require explicit `lab:run` and demo mode for fixed, serial, time-bounded test
subprocesses. Isolate coverage, manifests and SQLite per job; expose safe parsed
artifacts rather than raw process logs. Source changes during tests invalidate
release evidence. Keep the configured full-regression coverage gate distinct
from unit-only coverage and record the unmet proposed unit-only 85% target.
No learner milestone or real enterprise/production connection follows from this
assistant-authored build. Recovery and actual evidence are in the testing-layer docs.
