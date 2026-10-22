# Executable test plan

Acceptance contracts live in `requirements/acceptance_criteria.yaml`, including
AC-LAB-001–008. The criteria are definitions; current execution status comes from
fingerprint-bound reports rather than a static approval label.

| Layer / requirement | Inputs | Required assertion and evidence |
| --- | --- | --- |
| Unit / HR-005,014 | Seven intents and a changed routing YAML pattern | Configured pattern changes the route; every intent has a contract; malformed rules fail validation |
| Unit / HR-004,015 | Disabled deny-by-default, duplicate IDs, missing grant | Configuration cannot remove the fixed security invariants or grant permissions from prompt text |
| Unit / HR-009,010 | Successful and failed timed operations | Real nonnegative stage time; failed work differs from skipped work |
| Unit / HR-002,011 | Exact Decimal, negative, stale, wrong-tenant record | Valid value preserved; malformed, stale or mismatched adapter output rejected |
| Unit / HR-012,015 | Allowlisted suite, arbitrary command/path attempts | Fixed argv/environment; no inherited provider key or arbitrary shell command |
| Unit / HR-010,012 | Concurrent jobs, deadline, process failure, malformed artifacts | One active job; owned process cleanup; explicit safe failure, no assertion payload in web response |
| Integration / HR-002,014 | Change temporary SQLite balance to 10.75; replay unchanged seed | API returns stored 10.75 exactly; orchestrator has no hardcoded 12.5 answer |
| Integration / HR-001,004 | Revoke active identity in SQLite | 401 before source call, with a failed authentication stage |
| Integration / HR-004,010,011 | Revoke delegated scope or remove approved policy after receipt | Receipt replay conflicts safely; fresh request denies/abstains; no protected reread |
| Integration / HR-007,010 | Normal, 503, timeout, missing, malformed, stale, wrong owner, 429, intermittent | Expected status and exact attempt count; no cross-request fault state |
| Integration / HR-009 | Core policy/PTO/denial requests | Safe source metadata, matched rule IDs/config paths and measured stage outcomes |
| Integration / HR-012,015 | Employee, scoped HR and explicit lab admin; extra HTTP fields | Only explicit operator can start/read jobs; unknown suites and supplied commands/paths rejected |
| End-to-end / HR-001–006,010,015 | Signed Slack requests and repeated/concurrent events | Exact source response, cited current policy or denial before protected method; replay has no new read |
| End-to-end / HR-012,014 | Authenticated HTTP unit-job request | Actual subprocess creates actual JUnit/coverage and passing counts in isolated folder; canonical evidence unchanged |
| Performance / HR-009,010 | 25 ms mock delay; mixed concurrent fault profiles | Trace measures the delay; outcomes/attempts remain request-scoped |
| Evaluation / HR-003,005,006,007,015 | Independently authored routing/retrieval/answer/security JSONL | Explicit case IDs, labels, numerator/denominator, failure IDs and hard release gates |
| Browser / AC-LAB-001–006 | Personas, questions, failure selector, test buttons, mobile viewport | Actual request submission, source/rule/stage display, permission gates and real job results |

Run `make verify` for static checks, all five pytest directories, coverage and
the independent evaluations. The HTTP runner's `evaluations` suite executes the
same test directories before evaluating its own isolated artifacts. Unit,
integration and security buttons run only their named directories; partial
coverage is not a full release decision.

Metric definitions: Recall@5 and MRR use labeled relevant document IDs from up to
five ranked chunks. `precision_at_5` uses a fixed five-slot denominator across
positive queries; `returned_result_precision` reports precision among actually
returned unique documents separately. Coverage requires a relevant hit. Negative
retrieval cases check unauthorized/outdated exclusion and may retain authorized
distractors. Answer quality checks exact source support, labeled facts and safe
statuses; they do not establish comprehensive semantic groundedness or completeness.

Mandatory demo gates cover routing, recall, citations, extractive support, exact
PTO, critical security, zero observed exposure, answer cases, mock p95, concurrent
success, combined coverage, traceability and current passing test evidence.
Fingerprints include Python, configuration, fixtures, labels, scripts, test code,
CI and browser sources. A source change during a test run invalidates that evidence.
GitHub configuration is executable but a hosted GitHub run must be reported
separately from these local checks.
