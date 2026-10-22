# PeopleOps failure and recovery record

Updated: 2026-10-18. Historical setup incidents below are supported by the
[verification record](training/docs/verification.md). They are infrastructure
events, not learner mistakes. Active DEBUG tasks must initially record symptoms
and evidence without revealing the root cause.

| ID / state | Observed vs expected | Established cause | Resolution / evidence | Prevention |
| --- | --- | --- | --- | --- |
| F01 · Resolved setup failure | Compose export failed with “image already exists”; expected one usable image | Four services concurrently built/exported the same image tag | Only API builds shared image; full Compose startup subsequently healthy | Retain single image builder; inspect dependency/build graph before parallelizing mutations |
| F02 · Resolved setup failure | pytest could not import lab; expected local package import | Editable install occurred before package files existed | Reinstalled package and configured test pythonpath; foundation suite passes | Create package structure before install; retain import smoke |
| F03 · Open nonblocking warning | Starlette TestClient warns that its HTTPX path is deprecated; tests still pass | Installed library's deprecation path with locked HTTPX dependency | No migration performed; 30 foundation tests pass | Plan a bounded dependency migration when needed; do not suppress as evidence of a fix |
| F04 · Known container test warning | pytest cache cannot write /app; tests still pass | Non-root service user and root-owned source directory | Writable /tmp cache option is documented; no application defect claimed | Use pytest -o cache_dir=/tmp/peopleops-pytest-cache when running container tests |
| F05 · Expected exercise baseline | E01 raises PendingExercise rather than returning a normalized employee | Starter function intentionally has no implementation | Eight focused tests fail at that line; awaiting learner attempt | Keep scaffold failures separate from infrastructure failures and assessment scores |

## L2-001 verification

2026-10-18: existing Compose stack started without rebuilding. All four running
services reported healthy; seed exited 0. Foundation suite: 30 passed. Live smoke
passed health/readiness, authentication, fixture counts, pagination, actual mock
HTTP timeout, intermittent 503, and schema drift. Evaluation: 4 passed, 32 blocked,
0 executed failures. The eight E01 failures are intentional; no diagnosis of a
learner weakness follows from them.

## Future DEBUG record format

- Scenario ID, seed, isolated fixture/database/transport, exact trigger.
- Expected behavior, observed behavior, relevant logs and files.
- Learner hypothesis and a test that could falsify it.
- Investigation steps and actual evidence.
- Confirmed root cause only after investigation; distinguish it from guesses.
- Learner's fix, focused regression result, and baseline-preservation check.
- Prevention, production implications, assistance level, and linked attempt ID.

Never trigger faults against the default shared baseline during a learner
challenge. Use per-request mock scenarios, rollback fixtures, or a separate
database/transport. Stop or clean up only scenario-owned resources.

## Working policy app checks · 2026-10-19 (not learner failures)

- FACT: the first expanded run had 33 passes, two failures and a related teardown
  error. Benefits phrasing included generic “work”; the mock required that word.
  “Medical records” did not match the singular privacy pattern. Controlled fixes
  to word normalization and the plural pattern produced 35 passing checks.
- FACT: tightening PTO request selection exposed a missing “open” → “request”
  synonym in the offline payroll test. Added the synonym and a vocabulary hash
  to embedding-space identity. The complete host run passed 56 tests.
- FACT: the first container run passed 55 tests and failed its workflow contract
  check because the Dockerfile did not copy n8n JSON into the image. The corrected
  image includes the workflow; final container evidence is in the app's
  verification document. No learner score is assigned to these implementation fixes.

## Interactive app layer · 2026-10-20 (not learner failures)

- FACT: the first expanded run stopped with 80 passes and one duplicate-response
  assertion failure. Adding per-request timings and replay diagnostics changed
  the complete JSON while preserving its business result. Assertions now check
  stable facts, answer, citation, status and correlation fields plus no repeated
  protected call and explicitly skipped replay retrieval. Final: 127 passed.
- FACT: browser 503 simulation showed a legacy breadcrumb listing validation and
  formatting before successful execution. Stage-specific append points corrected
  it; all fault-profile tests assert that failed source reads do not claim a
  deterministic record response. The structured measured trace was also inspected.
- OPEN: unit-only coverage is 53.83% against the proposed 85% target; full regression
  combined coverage is 94.01%. These are separate scopes, not interchangeable scores.
