# Measurable acceptance criteria

## Governing protocol and source status

The learner's actual Standardized SRE Methodology is required for methodology-based assessment. Its attachment/path has not yet been identified, so methodology phase names, exact evidence requirements, phase ordering, and source-specific checkpoints are **UNASSIGNED**. No claim of methodology alignment or completion is made. The existing lab criteria below remain lab-specific criteria, not a replacement protocol.

Before methodology assessment, record the document title, revision, path/link, hash or revision ID, and exact phase/page/section references in INVESTIGATION_LOG.md. Populate the CHALLENGES.md mapping and the checkpoint register below from that source. Interpret scope limitations against actual clauses rather than inventing missing requirements.

## Independent review records

Report **investigation-process quality** and **proposed-correction effectiveness** separately, each with evidence and limitations. Do not combine them into an average or let a passing correction compensate for missing process evidence. A careful investigation can remain unresolved; a working correction can have an unsupported explanation.

| Review | Evidence assessed | Current status |
| --- | --- | --- |
| Investigation process | Learner's source-anchored phase decisions, evidence provenance, submitted reasoning, experiment records, and responses to contrary evidence | NOT ASSESSED; governing source pending |
| Proposed correction | Identified candidate/diff and actual regression, reconciliation, control, and recovery results | NOT PROPOSED / NOT EVALUATED |

The baseline results belong to environment preparation. They do not establish that the learner performed any methodology phase. Record supplied evidence and independent learner measurements separately.

## Methodology checkpoint register

Populate one row per applicable requirement from the actual source. Do not mark a checkpoint satisfied without its exact requirement and learner evidence.

| Checkpoint ID | Exact methodology phase / requirement | Source page/section | Applicable challenge(s) | Required evidence / exit condition | Learner evidence | Reviewer status / reason |
| --- | --- | --- | --- | --- | --- | --- |
| Unassigned | Awaiting actual document | Unassigned | C1–C5: mapping pending | Unassigned | None assessed | NOT OBSERVED |

Use MET, PARTIAL, NOT MET, NOT OBSERVED, or NOT APPLICABLE WITH REASON for individual checkpoints. An unsupported or unavailable capability remains a coverage gap with its reason; it does not count as MET. Do not invent a methodology pass threshold before reading the source.

Reviewer questions authorized by the learner's request, independent of unverified methodology wording:

- Which raw measurement supports this conclusion, and who produced it?
- What different outcomes did the submitted hypotheses predict before the experiment?
- Which control, held-constant conditions, and observation window make that comparison interpretable?
- What contradicts the preferred explanation, and what remains unmeasured?
- Does the claimed causal explanation follow from a controlled comparison, or only from correlation or a passing candidate?

Apply these questions to the learner's submission. Do not fill in causal answers or supply hints unless explicitly requested.

## Lab capability inventory for later source mapping

These are limits of the prepared configuration, not assertions that the unseen methodology contains these requirements. Classify actual clauses after reading the document. Do not manufacture incidents or expand infrastructure just to claim coverage.

| Capability or context | What this prepared lab can establish | Coverage limit |
| --- | --- | --- |
| Real source-to-consumer data delivery | Local MySQL, real connector/embedded engine, synthetic committed identities, original reporter fixture, existing controls | Claims limited to measured local runs and the declared delivery semantics |
| Evidence and repeatability | Pinned checkout/images/dependencies, command captures, SQL, JUnit reports, retained local state | Prepared baseline is supplied evidence; learner work must be separately documented |
| Existing restart/control behavior | An upstream snapshot/restart test is available and has preparer baseline evidence | Each new recovery claim still requires its own learner evidence |
| Production incident response and business impact | Local impact and safe experiment boundaries can be described | No real customers, production traffic, on-call handoff, production SLO/error-budget history, or production stabilization decision |
| Broker/warehouse/dbt boundaries | Not present in the chosen embedded workflow | No Kafka broker offsets/durability, warehouse serving boundary, dbt model/freshness run, or lakehouse metadata validation can be claimed |
| Observability signals | Existing application logs, SQL and test reports can be inspected | A complete distributed metrics/tracing/lineage backend is not established; mark any required missing signal explicitly |
| Deployment and fleet recovery | A local candidate can later be tested against preserved baseline evidence | No production canary, multi-host rollout, traffic-based rollback, or proof of fleet-wide recovery |

Some capabilities are supported elsewhere by Debezium, but are outside this prepared lab. Mark a requirement's actual scope and limitation precisely; do not call it impossible for the entire repository merely because this configuration omits it.

## Environment handoff

- Exact repository HEAD equals `1397c912f32f48a6be513c481d9a1a6077dc8836`.
- `git diff --exit-code` succeeds; the only added Java file is the reporter's test, identical to the SHA-256 in `pins.json`.
- Both runtime images match `compose.yaml`; Java and the Maven wrapper run in the container.
- MySQL reports version 8.2.0, binary logging enabled, ROW format, GTID OFF, and FULL row images.
- Original seed table has 14 rows and 14 distinct IDs. Startup, build, test, and workload outcomes have raw logs and real exit codes.
- No production credentials, exposed host database port, unrelated container changes, or application patches.

## Existing lab evidence criteria

These criteria describe what the chosen exercise can demonstrate. They are not asserted to be the unseen methodology's wording, phase order, or complete requirements.

1. Define the external contract before naming a cause. Reconcile the workload's expected 15,001 committed identities with actual consumer identities; report missing, unexpected, and duplicate identities separately. Verify the source rather than trusting the generator alone.
2. Cite an exact run, log/report, schema, query, and configuration for each factual claim. Separate observations from hypotheses and code-derived inferences.
3. Reproduce the same externally visible discrepancy on the pinned, unpatched application in at least two documented runs, or report the tested frequency and unresolved reproduction conditions honestly.
4. Supply at least two competing hypotheses and one discriminating controlled experiment. Explain what evidence contradicts your preferred explanation.
5. Localize the first supported failing boundary. Do not substitute a suspicious source line for a measured boundary.

## A future proposed correction

- The same meaningful regression fails before and passes after the proposed correction, without weaker assertions or historical fix imports.
- Relevant upstream unit and pipeline smoke checks run and pass after the correction.
- Source-to-consumer completeness and absence of unexpected identities are demonstrated. Physical duplicates are counted and assessed against the declared delivery contract.
- Failure/recovery behavior and a normal control run are tested under documented conditions. Explain material untested cases and timing/platform limits.
- The explanation connects the measured symptom, the responsible code path, and a causal intervention. Another engineer can reproduce both baseline and corrected results from the documented commands.

These are investigation criteria, not a disclosure of the cause. Setup success, an authentic reproduction, a diagnosis, and a corrected system are separate claims.
