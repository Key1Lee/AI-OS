# Investigation tasks

Work progressively. Keep your own evidence ledger. No stage requires reading a fix, later commit, or issue discussion.

The learner requested their actual Standardized SRE Methodology as the governing protocol. Its source file is currently unavailable. The challenges below are existing lab scaffolding; their current order is not asserted to be the methodology's phase order. Source-specific phase mappings and evidence gates remain unassigned until that document is read. Use INVESTIGATION_LOG.md to record your work, and distinguish provided preparation evidence from your own observations.

## Methodology mapping status

The rows identify existing deliverables only. They do not invent or substitute methodology phases. Fill the two unassigned columns from exact headings and page/section references in the actual document.

| Challenge | Applicable methodology phase / source reference | Evidence or exit condition required by that source | Existing lab deliverable available for mapping |
| --- | --- | --- | --- |
| C1: Establish truth | Unassigned: source needed | Unassigned | Contract, provenance, independent source/consumer measurements, test scope |
| C2: Localize a boundary | Unassigned: source needed | Unassigned | Data path, boundary status, supporting measurements or explicit unknowns |
| C3: Discriminate hypotheses | Unassigned: source needed | Unassigned | Competing predictions, controlled experiment, observations and hypothesis updates |
| C4: Make reproduction dependable | Unassigned: source needed | Unassigned | Unchanged external contract, original fixture provenance, frequency and control evidence |
| C5: Propose and validate a correction | Unassigned: source needed | Unassigned | Causal justification, separate candidate, unchanged oracle, actual validation results |

No methodology checkpoint is credited by this table. The learner chooses and performs the investigation; the reviewer assesses submitted evidence and gives hints only when explicitly requested.

## C1. Establish truth

State the expected relationship between committed source rows and consumer events. Distinguish logical identities from physical deliveries. Record the exact commit, dependency versions, server settings, and workload. Run the existing unit and smoke tests, then the reporter's workload. Preserve the command status and actual test reports.

Deliverable: independently measured expected and observed key sets, counts, missing keys, unexpected keys, duplicate identities, and completion criteria. State which values you measured and which remain unavailable. The original reporter test is one oracle; critically examine what its assertions prove and what they omit.

## C2. Localize a boundary

Draw the data path using the running test and existing architecture. Identify durable state, temporary buffers, and acknowledgment boundaries. For each relevant boundary mark PASS, FAIL, or UNKNOWN and cite evidence. Choose the next measurement that would reduce the largest uncertainty.

Deliverable: the earliest supported violating boundary, or an explicit statement that the current evidence cannot identify it.

## C3. Discriminate hypotheses

Propose at least two plausible mechanisms that make different predictions. Choose one controlled experiment. Change one relevant condition at a time and preserve the unpatched baseline. Prefer existing test facilities and synchronization over arbitrary delays.

Deliverable: predicted outcomes, observed outcomes, confounders, and the hypotheses the experiment supports or contradicts. A failed hypothesis is useful progress.

## C4. Make the reproduction dependable

After you understand the symptom, reduce workload or control scheduling without altering production behavior or weakening the contract. Explain why your test exercises the same external failure. Repeat under documented conditions and report the frequency, including non-reproductions.

Deliverable: a bounded reproducer, explicit failure assertion, source/consumer evidence, and a passing control case. No arbitrary event drops, altered application semantics, or prefilled failing outputs.

## C5. Propose a fix, then validate it

Only after you establish a causal explanation, propose the smallest correction. Explain how the code path produces the observed failure. Preserve the original regression test and add meaningful adjacent/recovery checks where needed. Request a critical review of your reasoning before implementation if useful.

Deliverable: a red-to-green comparison on the same contract, unchanged source data, no missing/unexpected logical identities, duplicates assessed under the actual delivery semantics, and relevant upstream controls still passing. A passing process exit alone does not meet this bar.
