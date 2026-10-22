# Business reasoning, grain and metrics — Step 3

Implemented as an extension of the existing learning framework: 60 original
cases, three displayed evidence variants per case, and LEARN, PRACTICE and
INTERVIEW modes. There are 183 curriculum problems in total, including the
unchanged 120 SQL/debug and three modeling/architecture representatives.
The separate ten legacy business architecture experiments remain available.

## Entry points

```sh
uv run lab-web --port 8089
# Open http://127.0.0.1:8089/learn?focus=reasoning
uv run lab-learn catalog --focus reasoning
uv run lab-learn recommend --focus reasoning
uv run lab-learn start REASON-TRANSLATE-001 --mode LEARN
uv run lab-learn view RUN_ID
uv run lab-learn act RUN_ID ask --answer-file question.json
```

Use the browser's Practice focus selector to switch between business reasoning,
SQL and the whole curriculum. SQL retains its PostgreSQL runtime; reasoning
requires no database service beyond the existing local SQLite learner store.
Use `--state-dir PATH` before a CLI subcommand for isolated practice profiles.

## Architecture and disclosure

`curriculum/business-bank.json` uses the existing `ae-problem-v1` contract with
`kind: reasoning`. Definitions join `PROBLEMS`; there is one `LearningEngine`,
one Store and one append-only Mastery ledger. `business_reasoning.py` supplies
stateless assessment helpers; it is neither a new application nor a governed
metric service. Five source families are copies of existing SQL fixtures;
IoT, workforce and AI sources are local synthetic fixtures. Step 2 source
definitions and SQL problem fingerprints remain unchanged.

The first screen shows only the stakeholder request, source schemas and source
rows. It does not disclose expected grain, guaranteed keys, clarification
categories, private pitfalls, reference facts, candidate diagnosis or solution.
Submitting the first question saves it for tutor assessment. Only then does the
workbook introduce structured fact questions, authorized policy labels and any
deliberately incorrect implementation. The learner declares source and output
grain before submitting calculations and recommendations. Explicitly requested
hints and solutions mark assistance.

Three fixture variants are `sample`, `edge` and `revisit`. Each is fully visible
before it is assessed. Hidden authoring tests do not reject a learner for
undisclosed rows. After an objective-correct attempt, a new evidence probe
introduces the next variant and resets requirements. Starting another session
for the same case rotates variants. Definitions and source snapshots are
SHA-256 pinned. Older attempts retain their exact answer, preparation and question
snapshot; reviewing one cannot complete a newer evidence variant.

## Curriculum and prerequisites

| Competency | Cases | Foundation |
|---|---:|---|
| Business Problem Translation | 6 | Entry point |
| Grain & Cardinality | 6 | Translation |
| Entity & Event Reasoning | 6 | Grain |
| Metric Definitions | 6 | Translation, entities |
| Join Fanout & Aggregation | 6 | Grain, metrics |
| Temporal Reasoning | 6 | Entities |
| Data Integrity | 6 | Entities |
| Business Dimensions | 6 | Grain, temporal |
| Analytical Validation | 6 | Metrics, integrity |
| Stakeholder Communication | 6 | Translation, validation |

`business-paths.json` describes this dependency graph. Each area has a core and
three subcompetencies: 40 new tracked concepts. Each has at least three available
tasks, multiple business contexts, diagnosis work and mapped recall prompts.
Prerequisites influence routing; deliberate manual selection remains available.
Availability is separate from observed learner coverage.

| Synthetic context | Cases |
|---|---:|
| IoT / connected vehicles | 10 |
| Commerce / retail | 7 |
| B2B SaaS | 8 |
| Payments | 5 |
| Logistics | 5 |
| Marketing attribution | 8 |
| Workforce | 8 |
| AI product telemetry | 9 |

Difficulty spans L1–L6: 2, 13, 23, 16, 5 and 1 cases respectively. The initial
reasoning recommendation is L3 for this experienced learner; self-report grants
no mastery. Weak competencies return in another business context, repeated
failures reduce difficulty, and due recall precedes another full problem.
Where an appropriate authored task is unavailable the selector reports a gap.

## Metric contracts and visual training

Nineteen metric cases require all ten fields: definition, entity/result grain,
numerator, denominator, eligibility, time window, attribution, missing/duplicate
rules, reconciliation and failure modes. Other cases require definition, grain
and reconciliation, with fuller reasoning judged against the case rubric.
Fields that do not apply require a reason; nonempty prose is only a structural
check and cannot establish semantic correctness.

| Required metric | Representative cases |
|---|---|
| Monthly active users | `REASON-METRICS-001` |
| Qualified leads | `REASON-TRANSLATE-002`, `REASON-FANOUT-002` |
| Customer conversion | `REASON-TRANSLATE-004` |
| Customer churn | `REASON-METRICS-002` |
| Gross / net revenue | `REASON-VALIDATION-001` |
| GRR / NRR | `REASON-METRICS-003` |
| Average order value | `REASON-METRICS-004` |
| On-time delivery | `REASON-METRICS-005` |
| Device uptime | `REASON-METRICS-006` |
| Employee headcount | `REASON-TRANSLATE-005`, `REASON-GRAIN-004` |
| Funnel conversion | `REASON-TEMPORAL-006` |
| AI task success | `REASON-TRANSLATE-006` |

Five cases support alternate labeled definitions: current/historical
qualification, final/any approved success, delivered/all-promised delivery
denominators and known/strict uptime. Their numeric references differ by policy;
a tutor assesses whether the choice and communication are defensible.
Thirty-eight cases include an actual incorrect candidate to diagnose and repair.

Visible source tables progress from headers and lines to retries, bridges,
effective histories and two independent many sides. Post-attempt join traces
show child identities or multiplicities, their resulting row combinations and
repeated measures. Unknown, absent, false and known zero remain distinct.

## Tutor-mediated ambiguity and semantic review

This is a local tutor-assisted simulator. The web app saves real learner
questions as `PENDING_TUTOR_REVIEW`; it does not automatically classify natural
language or fabricate an interactive stakeholder using keyword matches. Codex
or another named tutor reads the case and actual question, then uses the trusted
CLI to disclose only the relevant authored fact or a justified custom response.

```json
{"question":"Which decision will this number support, and why does that matter?"}
```

Question assessment uses exactly five categories: `essential`,
`documented_assumption`, `minor`, `overengineering`, `dangerous_assumption`.
The assessed question, stakeholder response, reviewer, rationale and timestamp
remain in the session ledger. Clarification itself is legitimate analysis and
does not mark the answer hint-assisted. No application credit is awarded for
asking alone.

Example trusted response file:

```json
{"reviewer":"Named tutor","category":"essential","rationale":"This question changes the population or decision the report must support.","fact_id":"decision"}
```

```sh
uv run lab-learn evidence RUN_ID
uv run lab-learn respond RUN_ID QUESTION_ID --response-file response.json
```

`fact_id` can select `decision`, `definition`, `clock`, `identity`, `rounding`,
`display`, `platform` or `unsafe`; its category must match. A tutor may instead
provide a `response` with a supported classification. Read the private case
definition to select facts; do not disclose the complete fact list before the
learner has asked. Each question is assessed once. The learner can refresh tutor
responses in the browser and continue with explicit pending/blocking assumptions.

Objective facts have exact typed checks: numeric equality using Decimal,
identity key sets, relationship labels and authorized policy results. Unknown
numeric results require JSON null, never zero or a nonfinite value. The first
failed fact receives a brief correction, relevant source evidence and a follow-up.
Correct source facts return `REVIEW_REQUIRED`, with no application evidence.

The tutor separately scores translation, clarification, grain/relationships,
metric definition, temporal/integrity reasoning, validation, communication and
tradeoffs; diagnosis cases also require causal fault diagnosis. Each case
contains rubric guidance, private resolution, common error and validation
strategy. Anchors: 0 absent/incorrect; 1 partial with a material gap; 2 defensible
and supported; 3 independently validated and proportionate about alternatives.
Every dimension needs at least 2 for approval. Each score requires an exact
quotation from the saved answer/preparation/questions plus a rationale.

```json
{
  "reviewer":"Named tutor",
  "rationale":"Overall assessment against this case's source contract.",
  "criteria":{"problem_translation":true},
  "concepts":["business.translate.core"],
  "judgment":{"problem_translation":{"score":2,"evidence":"EXACT QUOTE FROM SAVED ATTEMPT","rationale":"Why that passage supports the criterion."}}
}
```

This abbreviated example illustrates the shape; a real review must include
**every** authored criterion in both `criteria` and `judgment`, with matching
booleans. `concepts` must list only tags the tutor actually assessed. Objective
failure, fabricated quotes, missing scores, inconsistent booleans and duplicate
reviews are rejected.

```sh
uv run lab-learn review RUN_ID ATTEMPT_ID --review-file review.json
```

There is no public HTTP review or stakeholder-response endpoint. Trusted local
CLI review is an operator boundary, not secure examination authorization.
INTERVIEW hides rubric feedback and expected facts until completion, allows no
hints, and retains ambiguous requests plus open follow-up questions. LEARN and
PRACTICE require tutor approval before completion; interviews may close pending
review and retain their completed state when assessed later.

## Evidence and limits

The existing states remain UNSEEN → INTRODUCED → UNDERSTOOD → APPLIED → DEBUGGED
→ TRANSFERRED → MASTERED. Repeated variants share the same task identity.
Reviewed causal understanding, a distinct debugging task, different-domain
application after at least a day, three tasks, two recall days and a seven-day
span are still required. Hints, solution exposure and corrective feedback mark
later same-session answers assisted. A copied numerical answer earns no judgment
or automatic mastery.

No autonomous semantic model service, multi-user authentication, unlimited case
generation, production data connection, governed metric layer or Step 4 modeling
module is implemented here. The finite three-variant bank is repeatable local
training; transfer is evidence to develop over time. Tests demonstrate software
behavior, not that the learner has already acquired these skills.

Validation commands and observed results are in
[the verification record](business-reasoning-verification.md), machine receipts
in [business-reasoning-validation.json](business-reasoning-validation.json), and
the exact [file manifest](business-reasoning-files.md).
