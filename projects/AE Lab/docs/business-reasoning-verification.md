# Step 3 verification — 2026-10-15

The implemented extension provides 60 usable cases in the existing learning
surface. No Step 4 module or production-readiness certification is claimed.

## Observed acceptance evidence

| Criterion | Observed result |
|---|---|
| Exactly 60 original cases | PASS: six in each of ten competency areas; eight contexts; L1–L6 |
| Valid contracts | PASS: all definitions pass the existing JSON schema, concept registry, typed objective rules and pinned fixture checks |
| Source/reference agreement | PASS: 195 case/variant/policy combinations; independent hand-calculated sentinels in all eight contexts |
| Adversarial rejection | PASS: 510 single-fact mutations rejected; additional tests cover normalized duplicate keys, booleans, nonfinite numbers, null/zero distinctions, clocks, weights, retries and fanout |
| All three modes | PASS: 540 complete observation → preparation → submission workflows across 60 × 3 variants × 3 modes; separate completion/review tests for each mode |
| Judgment remains separate | PASS: objective-correct gibberish stays pending; rubric requires every score, actual saved quotations and rationale; fake/missing evidence and duplicate review rejected |
| Ambiguity simulator | PASS: real question ledger, five tutor classifications, gated individual responses and no public approval endpoint |
| Adaptive integration | PASS: L3 entry, prerequisites, weak-concept routing, different contexts, original mastery progression, distinct debugging and spaced recall |
| Repetition / assistance | PASS: one task identity across variants; corrective exposure marks later same-session answers assisted; unseen variants cannot be skipped or graded as already completed |
| Steps 1/2 regression | PASS: full project tests; all 120 SQL definition fingerprints match the existing Step 2 receipt |
| Existing progress | PASS: six baseline run documents and five learning-evidence records retain their hashes |
| Browser experience | PASS: first-question flow, requirements, answer submission, clarification refresh, source comparison, join trace, trusted review display and completion; no browser errors observed |
| First authentic handoff | PASS: `REASON-TRANSLATE-001`, LEARN/L3/sample, zero answers, attempts, hints or solution exposure |

## Executed commands

```text
uv run pytest -q
521 passed in 130.94s

uv run pytest -q tests/learning/test_business_reasoning.py tests/learning/test_web.py
84 passed in 4.42s

uv run python scripts/validate_business_bank.py
PASS: 60 definitions, 195 objective references, 510 rejected mutations,
      540 mode/variant workflows, 38 diagnosis cases, 5 multi-policy cases

node --check lab/web_assets/learning.js
node --check lab/web_assets/reasoning.js
PASS

uv run python scripts/curriculum_inventory.py
579 concepts; authored availability matrix regenerated
```

The focused 84-test run and final acceptance validator were repeated after the
last key-normalization hardening. The full run preceded that small hardening
and the final reviewed-feedback wording. The relevant focused suite covers
both changes. Final renderer-only changes passed JavaScript syntax checks and
were loaded in the browser.

During development, one new mastery test attempted its second recall before
the existing scheduler made it due. The test's simulated date was corrected to
respect that interval; the scheduler policy was preserved. An initial test
collection import was also corrected. No unresolved test failures remain.

## Preservation and isolation

The baseline was captured before Step 3 implementation in
`.lab/step3-baseline.json`. [Preservation receipts](business-progress-preservation.json)
compare all original IDs and SHA-256 values after the first new session was
created. The existing unanswered SQL session is still unanswered. The new real
session adds introduction evidence only. Automated cases and tutor-review
fixtures ran in temporary profiles; browser QA used `.lab/business-ui-*`.
No QA answers were inserted into the user's actual learning profile.

SQL fingerprint equality covers the 120 definitions in
`docs/sql-engine-validation.json`; the full suite additionally re-executes SQL
references against genuine PostgreSQL and exercises the native sibling
integration boundaries. Step 3 did not modify SQL fixture/runtime source or
those saved Step 2 receipts.

## Visual and machine receipts

- [All-case validation](business-reasoning-validation.json)
- [Progress preservation](business-progress-preservation.json)
- [Authentic first session](business-first-session.json)
- [Reviewed source facts and join trace](screenshots/business-reasoning-feedback.png)
- [Opening challenge, no answer](screenshots/business-first-session.png)

## Material limits

Semantic judgment and clarification classification require a trusted tutor.
The software verifies review completeness and quoted evidence; it does not
prove that a human/AI tutor's judgment is correct. There is no autonomous LLM
grader or stakeholder service. Reference prose in acceptance tests establishes
structural usability only, never learner judgment or mastery.

The three synthetic variants are finite. Manual case selection can bypass
prerequisite preferences; only valid saved evidence advances mastery. The local
CLI can inspect private keys and is an operator tool, not a secured examination
boundary. No multi-user or production-data validation was performed.

This verifies the local implementation and preservation of progress. It does
not establish that the learner has mastered business reasoning before practice.
