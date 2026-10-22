# Two independent assessments

## A. Investigation process

The governing sequence is the eight phases explicitly supplied in the extension request. It is supported by the original report's methodology section and [Google SRE: Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/), especially observations, competing hypotheses, and controlled tests. It is not represented as an official named Google eight-phase framework or as the previously unavailable separate methodology attachment.

Score each checkpoint **0: absent; 1: incomplete/unsupported; 2: reproducible and evidence-backed**. Record all eight scores independently of whether a fix passes. An accepted investigation requires 2 at each phase; pending phases remain pending. Existing preparer runs earn no learner credit.

| Phase | Required checkpoint |
| --- | --- |
| Business Contract | Expected identity, authorization, completeness, action/receipt, history, duplicate, and recovery claims are written before interpreting implementation. Scope and unsupported requirements are explicit. |
| Observe | Exact revision/versions/configuration, commands, real exit codes, raw evidence paths, and expected versus observed behavior are recorded. Fact, inference, and hypothesis are distinguished. |
| Reconcile | Every request is accounted for at inputs, model boundary, actions/results, external effects, and final output. Missing, extra, duplicate, foreign, and unauthorized records are measured independently of text success. |
| Localize | Runtime evidence establishes last known correct and first known incorrect observations. Code-based inferences are labeled; no root claim rests on inspection alone. |
| Hypothesize | At least two credible explanations have falsifiable, distinct predictions, supporting/contradictory evidence, and calibrated confidence. |
| Experiment | Prediction and control precede execution. Changed variables, confounders, stopping rule, raw outcome, and impact on each hypothesis are recorded. Weak or contradictory results are not discarded. |
| Reproduce | Another engineer can run the pinned reproduction, with the same failure signature at least twice, without credentials or timing guesses. Harness fidelity and boundaries are justified. |
| Validate | Proposed change has a causal before/after test, meaningful independently authored regression, existing-test evidence, full business reconciliation, and an explicit list of limits/remaining risks. |

The reviewer evaluates your submitted evidence, challenges unsupported claims, and supplies causal hints only upon explicit request. A correct-looking patch with a weak investigation fails this process assessment. A careful investigation can receive process credit while a proposed correction is rejected.

## B. Correction effectiveness

Each row is **pass / fail / unassessed**, with evidence paths and actual commands. No correction has been attempted by the preparer.

| Criterion | Measurable acceptance |
| --- | --- |
| Completeness | Both request IDs have exactly one correctly paired terminal output; two intended service effects exist. Every output's receipt equals its request's actual committed receipt. |
| Isolation | Zero foreign request/employee/tool-result identities in any request's model context, intermediate history, tool arguments, external effects, or completion. Inspect all rounds, not only final output. |
| History | Each normal request retains both expected inspect/apply observations, matched by request and tool-call identity. No missing or extra history entries. |
| Authorization | Baseline operations are within declared employee and service scope. Learner-authored negative probes for cross-employee, cross-service, or invalid-grant actions produce zero committed effects. Baseline zero denials alone is insufficient negative coverage. |
| Action consistency | HR creates a correction service record only; survey creates a draft only. Payload, principal, request ID, tool arguments/results, receipt, and output agree. Zero payments, publications, or invitations. |
| Duplication / retry | Exactly one committed intended effect per request. Any repeated API attempts are identified and explained. A learner-authored replay test must distinguish fixture idempotency from n8n delivery behavior. Durable restart recovery is unassessed in this harness. |
| Regression / determinism | Original 71 scoped tests still pass; each single-request control and the two-request contract pass; the independently authored failing-before/passing-after test reproduces consistently at least twice. Preserve assertions and record all revisions. |

The supplied business checker covers normal-case identity, receipts, effect counts, final history, and request references at the model boundary. Independently verify it; it does not certify all security or recovery requirements. Fix acceptance requires every applicable row to pass, with unsupported production requirements explicitly unassessed. Do not change the source pin, weaken fixtures, or import an upstream solution to obtain a pass.
