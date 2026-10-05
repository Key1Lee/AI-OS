# Independent Orchestration Verification — initial pass

Date: 2026-10-02, Asia/Seoul. Verifier: the single authorized Orchestration Verification Agent. This initial verdict concerns the implementation observed before the main agent's corrections; it is retained as the failure baseline. No implementation, product test, approved contract, sibling project, or shared AI-OS file was edited by the verifier.

**STATUS: FAIL**

Contract source: original user request, `AGENTS.md`, `docs/acceptance.md`, `docs/architecture.md`, and AI-OS `architecture/verification.md`. Implementation claims in `docs/implementation-handoff.md` were used as locators only. Scope is the bounded standalone first slice, including deterministic execution, five authored variations, three-date backfill, integration schemas, and beginner visual explanations. Production scheduling, SQL evaluation, assessment policy, monitoring, and live vendor integrations are excluded.

## TESTS EXECUTED

- Independently ran `npm test`: 27/27 passed. Evidence: `01-npm-test.log`.
- Independently ran `npm run build`: TypeScript and Vite succeeded. Evidence: `01-build.log`.
- Independently ran `npm run test:e2e`: 8/8 production browser journeys passed, including offline execution. Evidence: `01-e2e.log`.
- Independently authored and ran `independent-probes.test.ts`: 14/18 passed; four assertions contradicted the claimed contracts. Evidence: `01-independent-probes.log`. This run used a tee pipeline whose shell status was zero, but the recorded test runner explicitly reports four failed tests; the verdict is based on those failures.
- Independently authored and ran `independent-browser.mjs` against the production build on loopback 8078. Corrected selector run supports stage-first presentation, eight persistent questions, narrow layouts, no browser errors, and no external resources. It contradicts two additional UI behaviors. Evidence: `01-independent-browser-corrected-selectors.log` and the exported JSON. Earlier exact-text selectors accidentally selected hidden responsive copies; those selector failures are verifier errors, not product failures, and were corrected before the verdict.
- Inspected engine imports, state/trigger transitions, worker/pool allocation, Modeling adapter metadata handling, event/scenario schemas, UI labels, timeline, and production server. Reviewed desktop and mobile screenshots from the verifier's own required browser run.

## BLOCKING FAILURES

1. **Malformed runtime inputs accepted before later execution crashes.** `createRun(ecommerceWorkflow(), { partition: TODAY, initial_outputs: 7 })` accepts the number, then output writes throw. `{ mart_revenue: 7 }` is similarly accepted and crashes at mart output. With valid IDs A and B, `B.dependencies = 'A'` passes `validateWorkflow`/`createRun`, then dependency explanation/event creation throws because `.map` does not exist. These should fail at the public validation boundary. Two independent assertions reproduce the output-store and dependency-array gaps.
2. **Requested replacement can double an existing partition.** Using the unsafe-rerun workflow and a Sep 30 record with 100 rows, `planBackfill(..., 'replace')` promises explicit replacement, but `simulateBackfill` returns successful 200 rows. The engine should replace under an explicit compatible replacement policy or reject the incompatible append workflow truthfully, preserving Modeling ownership of write semantics.
3. **Retry explanations promise capacity that is unavailable.** A(duration 1, transient then success, delay 1) and B(duration 10) with one worker: A fails at 06:01, B occupies the worker until 06:11, and A's second attempt starts at 06:11. At 06:01, `whyTask(A)` says “Next attempt starts at 06:02”. That is eligibility time, not guaranteed start time. Timeline code additionally labels the whole interval between attempts as “Retry delay”, even when it includes capacity waiting.
4. **Backfill export omits the displayed runs.** Run Sep 27–29 successfully in Backfill Lab, then click the visible global “Export run evidence”. The download contains only the untouched Oct 2 pipeline run in WAITING, with none of the three displayed backfill runs, plan, historical partitions, or events. Preserved initial download: `01-backfill-export.json`.
5. **Accepted dates display the wrong month.** Set backfill start and end to 2026-08-01 and run. Its partition card says OCT / 01 rather than AUG / 01. Every non-September month is hardcoded as October. The actual text is retained in the corrected browser log. Year should also be shown when arbitrary prior-year dates are accepted.

All five findings were sent promptly to the implementation agent with reproductions. Their fixes belong to Implementation. No new architectural scope was requested.

## EXECUTION ERRORS

No dependency, compiler, browser, or service failure prevented the required checks. The malformed-input exceptions are product behavior covered by failure 1. The two initial browser-selector assertion errors were corrected in the verifier's own probe; they do not support product findings. Node's NO_COLOR/FORCE_COLOR warning did not affect the checks.

## ARCHITECTURAL VIOLATIONS

None demonstrated. The engine imports only its local TypeScript modules, uses explicit virtual dates/times and authored outcomes, and contains no wall clock, randomness, timers, AI, SQL evaluator, scoring, monitoring, or incident service. UI timers drive presentation only. Modeling grain/materialization remain opaque copied metadata. The append replacement defect is a behavior/contract failure, not evidence that the engine evaluates Modeling transformations. Vendor mappings and adapter types do not execute integrations.

## MISSING TESTS

The initial product suite lacks regressions for malformed nested output stores and string dependency arrays, append versus backfill replacement incompatibility, retry eligibility under capacity contention, exporting a Backfill run from its active view, and month labels outside September/October. Independent probes now retain the counterexamples. Calendar month/year/leap transitions and a reversed definition-order diamond were independently tested, supplementing the existing suite.

## UX FINDINGS

Stage-first overview, task reveal, success/failed/blocked distinction, inspector dependency truth, tasks/assets distinction, timeline attempt bars, readable desktop/mobile layout, and all eight persistent questions are supported by observed screenshots and browser checks. Failures 3–5 contradict explanation/export/date truth and prevent acceptance despite the authored happy-path browser suite passing.

## EVIDENCE

| Approved criterion | Observation | Initial status |
| --- | --- | --- |
| Deterministic, vendor-neutral DAG | Stable reordered diamond A→C/B→D, duplicate/unknown edges and self/distant cycles rejected; repeatable traces in required suite; local imports only. | Supported |
| Dependency/state correctness | Independent all-success retry/exhaustion, all-done terminal joins, one-success while another parent runs, skip/failure propagation, independent branch success; eight states only. | Supported |
| Simulator | Authored success/failure, 47-minute task timing out at 5 minutes for all three attempts, pool/worker bounds, virtual UTC midnight crossing. | Supported |
| Retry | Capacity release, exact eligibility delay, attempts/exhaustion correct; deterministic errors not retried. Explanation falsely promises start time. | Supported execution; contradicted explanation |
| Schedule/asset trigger | Daily 06:00 Seoul gate distinct from dependency readiness; manual/source asset starts early; unrelated or produced assets rejected; UTC offset and next-day completion tested. | Supported |
| Reruns/idempotency | 100→100 replace and 100→200 append; other logical partition and previous traces preserved; imported safety remains unknown. | Supported |
| Backfills/partitions | Sep 27–29 isolation and failed replay supported; historical keys use current execution date; global interval sweep with retries and three active partitions supports worker/pool constraints. Explicit append replacement yields 200 rows. | Contradicted |
| Critical path/timeline | Reversed diamond A2/B8/D5 yields 15 minutes; faster C does not shorten it; OR join first success and longest independent task tested; real attempt bars visible. Combined retry/capacity wait is mislabeled. | Supported calculation; contradicted explanation |
| Beginner UX | Overview before task graph; grounded failed/blocked distinction, eight questions, assets and narrow layouts supported. Retry promise, omitted backfill export, and wrong month conflict with visible truth. | Contradicted |
| Integration boundaries | Events from authored and independent custom workflows pass Ajv; Model parents mapped without SQL inference and metadata copied without aliases; no sibling imports. Public runtime input shapes are insufficiently validated. | Contradicted validation; boundaries supported |
| Automated checks | 27 tests, build, 8 production browser tests pass; independent counterexamples fail. | Supported required checks; contradicted acceptance |
| Independent verification | Exactly one tool-capable verifier, independent inspection/checks and preserved evidence. Blocking findings remain until re-verification. | Supported process; PASS unavailable |

## RECOMMENDED FIXES

Add boundary shape guards and regressions; reject incompatible append replacement or provide a genuinely compatible explicit replacement behavior; distinguish retry eligibility from capacity wait; expose/export Backfill evidence from the active view; derive month/year labels from partition dates. Reuse this same verification agent for the corrected code and production build. Completion requires a fresh PASS with every criterion supported.
