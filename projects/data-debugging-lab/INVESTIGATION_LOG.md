# Investigation log template

Copy this template for each investigation and retain its earlier entries when conclusions change. Empty fields mean unrecorded, never passed. The prepared evidence in BASELINE.md belongs to the lab preparer; cite it as supplied evidence and identify what you independently reproduced.

**Protocol status: awaiting the actual Standardized SRE Methodology.** This template records the categories explicitly requested by the learner. It does not define replacement phases, ordering, or gates. Enter exact phase names and source references only after the governing document is available.

## Investigation identity and governing source

| Field | Entry |
| --- | --- |
| Investigation ID / learner / reviewer | |
| Started / timezone / last updated | |
| Challenge ID(s) from CHALLENGES.md | |
| Methodology title / author / revision | Awaiting source |
| Methodology file path or authoritative document link | Awaiting source |
| Source SHA-256 or document revision ID / date read | |
| Exact applicable phase name(s) and page/section references | Unassigned |
| Required evidence / checkpoint / exit condition from that source | Unassigned |
| Scope, exclusions, and authorized local actions | |
| Repository baseline SHA / candidate SHA or diff, if any | |
| Container digests / dependency manifest / server settings | |
| Previous preparation evidence reused, with its original author | |
| Learner-produced evidence, separately identified | |

## Symptoms and expected behavior

- Reported symptom, source, and time:
- Independently observed symptom and run ID:
- Expected behavior and authority for that expectation:
- Falsifiable data contract, logical identity, scope, and observation window:
- Expected versus observed behavior, with raw evidence references:
- Known impact in this local run; wider impact not established:
- Environment/setup failure or application discrepancy; evidence for the classification:
- Facts established so far:
- Assumptions and missing observations:
- Current exact methodology phase / source reference / reason for entering it:

## Evidence register and timeline

Use FACT, ASSUMPTION, HYPOTHESIS, or CODE-DERIVED INFERENCE explicitly. Distinguish supplied baseline evidence, learner measurements, and AI suggestions. A tool or model statement without a supporting measurement remains a claim to evaluate.

| Evidence ID | Time / run | Author / origin | Classification | Raw artifact and precise location | Direct observation | Scope / limitations |
| --- | --- | --- | --- | --- | --- | --- |
| EV-001 | | | | | | |

| Time | Action / event | Operator | Configuration or state change | Evidence ID | Outcome |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Hypothesis register

Write predictions before the corresponding experiment. Keep rejected and revised hypotheses with the evidence that changed your view.

| ID | Falsifiable explanation | Supporting evidence | Contradicting evidence / alternative | Predicted distinguishing observation | Confidence and reason | Status |
| --- | --- | --- | --- | --- | --- | --- |
| H-001 | | | | | | Untested |
| H-002 | | | | | | Untested |

## Experiment record (repeat for each experiment)

### EXP-001

- Exact methodology phase / source requirement / checkpoint:
- Question and linked hypothesis IDs:
- Predictions for each competing hypothesis, recorded before execution:
- Control or comparison and why it distinguishes those predictions:
- Initial state, data identity/window, exact SHA, dependencies, and configuration:
- Independent variable; conditions held constant; possible confounders:
- Existing test/fixture reused; any diagnostic changes and their diff:
- Exact command, SQL, or procedure:
- Allowed local scope, resource bounds, stop condition, and state restoration:
- Observation to collect; success/failure criteria and observation deadline:
- Execution status: NOT EXECUTED / EXECUTED / INTERRUPTED:
- Operator and start/end time:
- Run directory, raw logs/reports, query results, and exit code:
- **Observation** (measured output only):
- **Interpretation** (with evidence IDs and uncertainty):
- Which predictions were supported or contradicted:
- Unexpected results, confounders, missing measurements, and non-reproductions:
- Hypothesis updates and reason for the next action:

## Conclusions and checkpoint decisions

- Supported conclusion and evidence IDs:
- Remaining alternatives and evidence against the preferred explanation:
- Causal claim, if any; controlled comparison or intervention supporting it:
- Unknowns and limits on generalizing beyond this run:
- Exact methodology exit condition; evidence establishing it:
- Decision: CONTINUE / CHECKPOINT MET / UNRESOLVED / NOT APPLICABLE (with reason):
- Reviewer challenge, learner response, and resulting change in reasoning:

Do not record an untested explanation as an established cause. A correction that happens to pass a test does not by itself establish the explanation.

## Validation results (separate from process quality)

Correction proposed: YES / NO. If no correction is proposed, leave correction validation NOT EVALUATED. Keep the original buggy checkout and reports available; record proposed changes as a separate candidate/diff.

| Validation ID | Exact source criterion / invariant | Baseline evidence | Candidate command and version | Actual result / exit code | Evidence reference | Limitations |
| --- | --- | --- | --- | --- | --- | --- |
| VAL-001 | | | | NOT EXECUTED | | |

- Source identities / consumer identities / missing / unexpected / physical duplicates:
- Delivery semantics used to assess duplicates:
- Normal control, recovery, and adjacent behavior exercised:
- Repetitions and observed reproduction frequency, including failures to reproduce:
- Changes to test oracle or fixture, and justification independent of the candidate behavior:
- Checks skipped, unavailable, failed, or not executed:
- Supported correction outcome and residual risks:

## Methodology applicability and coverage

Only list actual requirements after reading the governing document. A missing capability is a coverage limit, not permission to fabricate an incident or add a new service.

| Exact phase / requirement and source reference | Required evidence | Applicable to this lab? | Available evidence or missing capability | Supported adaptation, if any | Reviewer coverage decision |
| --- | --- | --- | --- | --- | --- |
| Awaiting actual source | Unassigned | UNASSESSED | | | |

## Two independent reviewer records

### Investigation-process review

- Methodology source verified:
- Exact checkpoint IDs / source references assessed:
- For each checkpoint: MET / PARTIAL / NOT MET / NOT OBSERVED / NOT APPLICABLE WITH REASON:
- Evidence provenance and learner's independent work:
- Unsupported conclusions, weak experiments, missing evidence, or unaddressed contradictions:
- Process judgment: NOT ASSESSED / ASSESSED (with criterion-by-criterion findings):
- Required process improvements and next evidence needed:

### Proposed-correction review

- Candidate identity and test-oracle integrity:
- Validation evidence IDs:
- Outcome: NOT PROPOSED / NOT EVALUATED / WORKS WITHIN TESTED SCOPE / DOES NOT MEET CRITERIA / INCONCLUSIVE:
- Tested scope, unresolved cases, and limitations:

Record these judgments independently. A working correction cannot supply missing investigation evidence; a rigorous investigation may honestly end with an unresolved cause or unsuccessful correction.

## Reviewer interactions and requested hints

| Time | Learner request | Review question or feedback | Hint explicitly requested? | Assistance actually given | Learner's response / new evidence |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Do not prefill hypotheses, causal mechanisms, experiments, conclusions, or solutions on the learner's behalf. Review the submitted reasoning and evidence; give hints only on explicit request.
