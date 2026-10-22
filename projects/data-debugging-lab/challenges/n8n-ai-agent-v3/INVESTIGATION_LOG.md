# Investigation record template

Copy this file into a learner-owned log before editing it. Keep raw run evidence immutable.

## Session / provenance

- Investigator / UTC date:
- Governing protocol source: user extension request, eight-phase sequence; report methodology section / Google SRE supporting references:
- Source revision / tracked diff / fixture hash:
- Runtime and dependency versions:
- Synthetic inputs, configuration, command, true exit status:
- Run artifact directory:
- Safety boundary / unexercised requirements:

## Business Contract

| Request ID | Employee / allowed scope | Intended effect | Expected output/receipt | History / isolation / duplication rules |
| --- | --- | --- | --- | --- |
| | | | | |

Expected recovery behavior and what this environment can actually exercise:

## Observe

- Symptom and business impact:
- Expected versus actual:
- OBSERVED FACT (artifact + exact record/field):
- CODE-DERIVED INFERENCE (source + assumptions):
- HYPOTHESIS (not yet observed):
- Unknowns / contradictory evidence:

## Reconcile

| Request ID | Input | Model contexts | Tool calls/results | API attempts / effects | Output / receipt | Missing / extra / foreign / duplicates |
| --- | --- | --- | --- | --- | --- | --- |
| | | | | | | |

## Localize

- Path and evidence for each observation point:
- Last verified correct observation:
- First verified incorrect observation:
- What this does / does not establish:

## Hypothesize

| ID | Explanation | Supporting evidence | Contradictions | Distinct prediction / falsifier | Confidence |
| --- | --- | --- | --- | --- | --- |
| H1 | | | | | |
| H2 | | | | | |

## Experiment (repeat per experiment; fill prediction before running)

- Experiment ID / phase / hypothesis IDs:
- Prediction for each explanation:
- Control / deliberately changed variable:
- Confounders / stopping rule:
- Exact command / revision / fixture / configuration:
- Observation + raw artifact references / exit code:
- Conclusion supported by this experiment:
- Explanations weakened / strengthened / still indistinguishable:
- Next decision and why; no inferred fact from AI output alone:

## Reproduce

- Minimal reproducible command / setup / assertion:
- Two independent run directories and stable failure signatures:
- Harness fidelity and reproducibility limits:
- Independent reviewer replication:

## Validate (leave pending until a correction is proposed)

- Proposed correction revision and rationale:
- Failing-before / passing-after evidence:
- Existing tests and independently authored regression:
- Per-request reconciliation, isolation, negative authorization, duplicates, and replay:
- Remaining risks / requirements not exercised:
- Final causal conclusion, confidence, and contradictory evidence addressed:

## Review verdicts (separate)

- Process checkpoint scores /16, pending phases, evidence gaps:
- Correction criteria pass/fail/unassessed, evidence for each:
- Reviewer challenges / response / revised conclusion:
- Hints explicitly requested and received (if any):
