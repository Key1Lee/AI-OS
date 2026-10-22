# Interview and learning evidence

## Scoring rubric — ASTRA Level 2

This rubric supersedes the earlier five-category rubric. Score each learner
attempt out of 10, retaining category scores and assistance used.

| Category | Maximum points | Evidence |
| --- | ---: | --- |
| Correctness and passing tests | 3 | Meets the specified contract; meaningful tests actually pass |
| Code clarity and maintainability | 2 | Clear names, understandable flow, appropriate boundaries |
| Edge cases and error handling | 2 | Invalid, missing, empty, or conflicting inputs handled deliberately |
| Independent problem solving | 1 | Learner develops the reasoning and implementation without a supplied algorithm/solution |
| Production tradeoffs | 1 | Explains a relevant operational tradeoff and its consequences |
| Ability to explain the solution | 1 | Explains why the code works in their own words |

A score is evidence for this attempt, not a readiness percentage. Passing tests
alone does not satisfy the explanation or mastery requirements. Do not score
untouched stubs as failed learner attempts.

## Assistance ladder

| Level | Assistance permitted |
| --- | --- |
| 0 · Independent | Requirements, examples, contracts, and tests; no solution strategy |
| 1 · Conceptual | Explain the relevant concept without code |
| 2 · Algorithm | Describe an algorithm in plain English |
| 3 · Pseudocode | Logical steps without Python syntax |
| 4 · Guided | One line or small block at a time with learner participation |
| 5 · Worked | Complete solution only when explicitly requested, or during an agreed review after the learning exercise |

Start at Level 0 or 1 based on demonstrated evidence. Do not increase the level
automatically after a failed attempt. Record requested help, actual help, highest
level used, and whether an earlier solution was visible. Reduce assistance on
equivalent variations when evidence supports doing so. INTERVIEW mode has no
hints unless the learner requests one.

## Session L2-001 · 2026-10-18

- Mode: BUILD for state setup and verification; handoff to LEARN.
- Current exercise: E01 normalize_employee, Phase 1.
- Reason for selection: first incomplete milestone; tests translation of a
  concrete HR data contract into a small pure Python function.
- Assistance for this checkpoint: Level 0; no algorithm or implementation given.
- Prior context: earlier materials named programming concepts and supplied
  examples; no learner implementation or explanation has been submitted.
- Pre-code prompt: identify input, required output, correctness rules, intended
  data structure/operation, and likely edge cases. See NEXT_TASK.md.
- Attempt status: **not submitted**.
- Baseline: eight tests fail at the existing PendingExercise line. This is a
  scaffold check, not a learner score or evidence of weakness.
- Score/category scores: **not assessed**.
- Demonstrated strengths/weaknesses: **not assessed**.
- Production explanation / independent variation: **not assessed**.
- Decision: wait for the learner's requirements-to-code explanation, then their
  implementation. Do not assign E02 or provide a solution automatically.

## Append an attempt record after actual work

Record: date/session ID, exercise/variation ID, mode, task prompt, learner's
pre-code explanation, changed files, exact test commands/results, each rubric
score, total/10, help requested, help provided, highest assistance level,
observed strength, observed error, learner's production explanation, independent
variation evidence, and advance/remain decision. Unknown fields stay unassessed.

For DEBUG mode, capture the learner's hypothesis before revealing a confirmed
cause. For INTERVIEW mode, retain the original question and answer evidence;
do not rewrite an answer to make it appear stronger.

## Session PI-001 · 2026-10-20

- User explicitly requested a Principal Engineer hiring interview covering the
  working AI system and its data flow, one question at a time.
- Mode: INTERVIEW; assistance Level 0; no unsolicited hints. Earlier walkthroughs
  were visible, so the first flow explanation is not evidence of unseen mastery.
- Scope: `policy_assistant/` and its local n8n workflow, not learner exercise completion.
- Planned coverage: architecture and end-to-end flow; ingestion/versioning;
  embeddings/retrieval; grounded answers; authentication/authorization; n8n
  contracts; privacy and prompt injection; reliability; evaluation/observability;
  scaling and design tradeoffs. Ask only the current question and adapt later ones.
- Oral rubric, preserving the six category weights: technical correctness 3;
  clarity and architecture organization 2; edge cases/failure handling 2;
  independent reasoning 1; production tradeoffs 1; ability to explain why 1.
  No implementation or test credit is inferred from an oral response.
- Question 1: A US employee asks “How do I request PTO?” Walk me through the
  request from the chat screen until the employee sees a cited answer, explaining
  what each component does along the way.
- Answer, score, observed strengths/gaps: not submitted / not assessed.
- n8n editor currently shows first-time owner setup; account/password entry is
  left to the user. The interview can begin while that setup remains pending.
- Existing E01 checkpoint is preserved; no exercise or mastery status advanced.
