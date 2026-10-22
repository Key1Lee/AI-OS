# Staff AI Engineering interview practice

The objective is to explain and independently implement the actual system,
including its limits. Begin each checkpoint with a two-sentence business problem
and an actual fixture. Request one function/query, run its tests, then discuss
production impact before assigning the next step.

## Score each attempt out of 10

The ASTRA Level 2 rubric below supersedes the original rubric. Record attempts
and actual assistance in [INTERVIEW_LOG.md](../../INTERVIEW_LOG.md); readiness
and mastery evidence belong in [SKILL_MATRIX.md](../../SKILL_MATRIX.md).

| Dimension | Points | Evidence |
| --- | ---: | --- |
| Correctness and passing tests | 0–3 | Meets the specified contract; tests actually pass |
| Code clarity and maintainability | 0–2 | Clear names, control flow, and appropriate boundaries |
| Edge cases and error handling | 0–2 | Invalid, missing, empty, or conflicting inputs handled deliberately |
| Independent problem solving | 0–1 | Learner develops the reasoning and implementation independently |
| Production tradeoffs | 0–1 | Explains a relevant tradeoff and its consequences |
| Ability to explain the solution | 0–1 | Explains why the code works in their own words |

0–3: major gaps; 4–6: partial implementation; 7–8: sound with specific areas
to improve; 9–10: robust reasoning and implementation with explicit limits.
Scores describe this attempt, not a hiring prediction. Passing tests alone is
insufficient. Record learner explanation separately from implementation status.
An untouched placeholder is not a scored attempt. Mastery requires an equivalent
variation solved independently, passing tests, and an explanation. In INTERVIEW
mode, provide no hints unless requested; log any assistance given.

## Phase 7 interview sequence

1. **Python, 15 minutes:** normalize the actual Maya record without mutation.
   Add one meaningful negative case and explain batch/quarantine policy.
2. **SQL, 15 minutes:** headcount after joining employees to tickets. Explain
   why COUNT(*) changes and demonstrate a correct grain without relying on luck.
3. **Integration debugging, 10 minutes:** page2 times out and repeats. Show the
   causal evidence, retry budget, and conditions for rejecting partial results.
4. **RAG, 10 minutes:** an answer cites PTO v1. Is the failure ingestion,
   filtering, retrieval, or generation? Design one discriminating test.
5. **Authorization, 10 minutes:** a manager edits an employee ID in the URL.
   Explain principal trust, record scope, response minimization, and enumeration.
6. **Agent actions, 15 minutes:** confirmation is double-clicked, then the process
   dies after commit. Explain the receipt, lock, transaction, and replay behavior.
7. **Evaluation, 10 minutes:** accuracy rises while 80% of cases are blocked.
   Explain why coverage invalidates the headline and how to classify failures.
8. **Staff judgment, 10 minutes:** prioritize one production risk with a measured
   acceptance criterion and one alternative you would reject.

## Category C design extensions (not implemented)

- Replace local identity switching with SSO and assigned-case/recruiter scopes.
  Decide whether to add PostgreSQL row security as defense in depth.
- Replace lexical hash vectors with a versioned semantic model. Measure recall
  and leakage before choosing HNSW or a separate vector service.
- Add employment episodes/history and recruitment applications. Reconcile old
  metric contracts and run an explicit schema/data migration.
- Add transactional outbox delivery to a simulated external Slack receiver.
  Handle the crash-after-send-before-ack window; do not claim exactly-once.
- Add CI gates for foundation, completed exercises, SQL contracts, and strict
  evaluation coverage. Define how unfinished exercises remain intentionally red.
- Add concurrency tests and load measurements before caches, queues, replicas,
  or distributed workers. Explain cache keys that include permission scope.
- Compare a single deterministic tool router with multiple agents. Justify any
  added agent by a measurable need, isolation boundary, and recovery strategy.
- Define latency/error/privacy objectives, bounded tracing retention, cost
  controls, and an operational escalation path.

For each extension: specify the problem, invariant, measurable outcome, smallest
design, failure mode, and rejected alternative. No multi-agent system, CI/CD
pipeline, or production rollout is implied by this document.
