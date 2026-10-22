# Interview training mode

The latest ASTRA prompt governs this directory. Category A infrastructure is
implemented by the assistant. Category B business logic stays in `exercises/`:
provide signatures, examples, expected outputs, and failing tests. Do not solve
these functions until the learner attempts them and requests help; a failed
attempt does not authorize automatically supplying the answer.

Keep the old completed demo outside this learning path. Do not read or copy its
business implementations to answer an exercise. Default pytest checks only
foundation plumbing. Exercise tests must fail honestly when unfinished.
Never mark learner understanding complete based only on passing tests.

Run `uv run pytest` for foundation changes. Database tests require
`LAB_DATABASE_TESTS=1 uv run pytest -m database` against this isolated database.
All services and identities are fictional local demonstrations. External LLM
use requires explicit configuration and is not part of default startup/tests.
Do not expose the mock source or fixture explorer as a secure employee API.

## ASTRA Level 2 session protocol

Read the six state files in the project root (`../PROGRESS.md`,
`../SKILL_MATRIX.md`, `../INTERVIEW_LOG.md`, `../DECISIONS.md`,
`../FAILURE_LOG.md`, `../NEXT_TASK.md`) and inspect current learner code before
making changes. Recheck only relevant behavior; do not infer success from a
previous summary or model/schema existence. Preserve learner edits and untouched
challenges. No working implementation is supplied merely because tests fail.

Modes:

- BUILD: infrastructure, mocks, fixtures, environment, and safe scaffolding.
- LEARN: business story → actual input → expected output → learner's plain-English
  algorithm → existing signature → learner implementation → tests → explanation.
- DEBUG: isolated reproducible fault; provide symptoms, logs, expected behavior,
  files and tests; require a hypothesis, investigation, fix and regression proof.
  Do not reveal the cause in advance or disrupt the working baseline.
- INTERVIEW: realistic project question, no unsolicited hints, explicit rubric.

Before every implementation task, ask the learner to identify input, output,
correctness rule, data structure/SQL operation, and edge cases. Resolve unclear
reasoning before implementation. In LEARN, ask for the learner's algorithm;
supplying an algorithm is Level 2 assistance, not an automatic introduction.

Use assistance 0=requirements/tests, 1=concept, 2=plain-English algorithm,
3=pseudocode, 4=one line/block at a time, 5=worked solution. Start at 0 or 1
based on evidence; never increase automatically after one failed attempt.
Record actual assistance in INTERVIEW_LOG.md. Complete solutions require an
explicit request or an agreed post-exercise review; never silently fill stubs.

Score using the exact six-category rubric in INTERVIEW_LOG.md: correctness 3,
clarity 2, edge/error handling 2, independence 1, tradeoffs 1, explanation 1. Do not
invent a score for a scaffold baseline or a self-reported skill. Mastery requires
an equivalent independent variation, passing tests, and a learner explanation.

Every assigned task needs business context, synthetic example, requirements,
signature/query, expected output, edge cases, tests, failure scenario, production
implications, and a Staff follow-up. Add advanced requirements only after the
base case is understood. Later security/chaos requirements stay explicit pending
milestones; don't solve all exercises while preparing infrastructure.

Present the session handoff with: Current phase; Current system status; Today's
business problem; Interview skill; File to modify (project-relative path);
My task; Verification (exact command); Completion criteria. Then stop for the
learner. Assign only one task. Update the six state files with evidence, not
assumptions. Never equate generated infrastructure with learner readiness.
