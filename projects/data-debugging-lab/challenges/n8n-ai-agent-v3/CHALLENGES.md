# Progressive investigation

Do not read issue discussions, later history, or historical fixes. The issue link in `pins.json` is provenance and may spoil the exercise. The preparer's baseline is input evidence, not your investigation credit.

| Challenge | Applicable phases | Required evidence / checkpoint |
| --- | --- | --- |
| 1. Can both employees trust their service results? | Business Contract → Observe → Reconcile | Write expected identity, scope, action, history, and receipt rules first. Capture a run and independently join input → action → effect → completion. Separate measurements from interpretation and list unknowns. |
| 2. Where does the observed contract first cease to hold? | Localize | Draw the request path from repository evidence and runtime artifacts. Identify the last verified correct observation and first verified incorrect observation. Preserve competing explanations; do not nominate a faulty component from an error message alone. |
| 3. Which explanation survives an experiment? | Hypothesize → Experiment | Record at least two plausible explanations, their differing predictions, a control, one deliberately changed variable, and a stopping rule before execution. Preserve contradictory results and reassess your confidence. |
| 4. Can another engineer reproduce the business failure? | Reproduce | Supply exact revision, fixture, command, settings, assertions, expected/actual results, and at least two matching failure signatures. Exclude volatile timestamps/ports. Independently validate the harness's observation boundary. |
| 5. Does your proposed correction satisfy the contract? | Validate | Only after your reproduction, propose a minimal source change in a separate branch/copy. Show before/after behavior, existing tests, your independently authored regression, negative authorization/isolation checks, and effect reconciliation. Review process and correction effectiveness separately. |

Use [INVESTIGATION_LOG.md](INVESTIGATION_LOG.md) for every experiment. The reviewer will challenge unsupported conclusions, tests that cannot distinguish your hypotheses, missing controls, changed fixtures that weaken the contract, and validation that ignores business side effects.

## Realistic limits

This track can exercise evidence collection, request identity tracing, business reconciliation, controlled package-level experiments, bounded tool-call continuation, and deterministic regression validation. It cannot establish production SLOs, incident response under live customer impact, high availability, durable crash recovery, full queue/scheduler behavior, real HR/Qualtrics authorization, live model nondeterminism, or deployment/canary/rollback safety. Mark those requirements **not exercised** with this boundary as evidence. Do not manufacture failures or substitute mock guarantees for production evidence.
