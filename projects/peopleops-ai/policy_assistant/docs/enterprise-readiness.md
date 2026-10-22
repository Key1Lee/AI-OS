# Operational readiness assessment

This is a tested **fictional local reference candidate**. Its gates certify only
the described fixtures and measurements. No deployment to production, real Slack
installation, real Workday request, real employee record, or GitHub-hosted CI run
was performed.

| Control | Implemented evidence | Remaining production work |
| --- | --- | --- |
| Identity | Hashed mock bearer sessions, active principal, Slack user/workspace binding | Organizational SSO, account linking, revocation, token rotation and real lifecycle |
| Resource authorization | Self PTO; exact delegated target and approved mock purpose; HR role alone insufficient | Owner-approved least privilege, case-based delegation, purpose and consent policy |
| RAG governance | Registry metadata/digests, lifecycle/group/country/role filters before text/ranking, exact citations, index-tamper checks | Human policy approvals, authoritative jurisdiction rules, adversarial red-team review |
| Source safety | Typed exact PTO values, unit/as-of date, freshness bounds, source-owner check | Real adapter contract, units/accrual semantics and change-notification behavior |
| Reliability | Safe-read retries, capped backoff, timeouts, rate limiting, duplicate receipts, concurrency tests | Distributed coordination, durable queues, idempotency across workers and operational load testing |
| Observability | Allowlisted JSON logs, durable request events, per-request source status/timing, aggregate latency and ingestion freshness | Central telemetry, retention, access review, alerts and real incident ownership |
| Evaluation | 105 labeled cases, negative security tests, source support checks, ranking/chunk experiments, coverage and fingerprint-bound gates | Representative business corpus, broader language evaluation, independent adversarial data, semantic reviews |
| Deployment | Locked Python environment, local launchers, CI configuration and artifacts | TLS, secret manager, DB least privilege/encryption, network policy, backup/restore, migrations and authorized rollout |

## Proposed SLIs, SLOs and alerts — not measured production commitments

- Availability SLI: successful supported requests / valid supported requests.
  Proposal: 99.9% over 30 days, subject to stakeholder and workload review.
  The illustrative error budget is 0.1%; do not infer availability from unit tests.
- Latency SLI: full request p50/p95/p99 by workflow. Proposal: policy p95 <2 s
  and exact-record p95 <1 s under an agreed load. The actual demo gate is local
  in-process mock p95 <750 ms and is reported separately.
- Freshness SLI: source as-of age and time since the last successful inventory
  ingestion. Current record gate: at most seven days relative to the explicit
  fixture business date. Proposal: alarm after a missed hourly ingestion or an
  approved policy update not reflected within its agreed publication window.
- Security alert proposals: any unauthorized source exposure, unexpected tool
  request, or signature-failure spike; investigate without copying raw questions.
- Error-budget alert proposal: multi-window burn detection (for example 14.4x
  over one hour and 6x over six hours), tuned after actual traffic is known.
- Evaluation drift proposal: run representative offline suites on each policy
  publication and release; block critical security regressions, investigate
  recall/citation or semantic-quality degradation with a human policy owner.
- Audit review proposal: restrict audit access to approved operators and review
  operational exceptions weekly. Retention and deletion rules require approval.

## Incident and rollback playbook

1. Identify affected workflow and correlation IDs using redacted audit data.
2. If identity, source correctness or policy authority is uncertain, deny or
   abstain; never fall back to old public permissions or fabricate a balance.
3. Reproduce faults only in temporary mock databases/transports. Keep source
   payloads, tokens and employee identifiers out of logs and incident messages.
4. Preserve the current SQLite file before deliberate data changes. Reproduce a
   candidate in a fresh file using the governed registry and `make verify`.
5. Roll back application code/configuration with the prior known candidate and
   its compatible database copy. A policy revocation must not be undone by an
   older index; publish a new governed version or remove current inventory
   membership to deny access. Do not silently reapprove immutable history.
6. Require an actual owner to authorize production actions. The supplied GitHub
   workflow validates a candidate and uploads evidence; it does not deploy.

Limits include a small English corpus, lexical retrieval, in-process rate limits,
SQLite serialization, synchronous signed-event processing and explicit demo
identity switching. Real Slack needs its acknowledgement/queue behavior designed
and tested. Zero observed leaks is bounded evidence, not proof of absolute safety.
