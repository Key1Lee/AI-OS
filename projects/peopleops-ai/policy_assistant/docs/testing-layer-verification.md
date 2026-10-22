# Interactive layer execution evidence · 2026-10-20

Contract: the user's attached “Build and Test an Enterprise HR AI Assistant”
prompt, added to the existing local PeopleOps app. The functional engineering
layer is supported by executed HTTP, browser, subprocess and regression evidence.
All 13 configured demonstration gates pass. The proposed **unit-only 85% coverage**
target remains unmet; the enforced full-suite coverage gate has a different,
explicit scope. No production acceptance or independent security certification
is claimed.

## Actual regression and evaluation results

Executed from the project directory:

```sh
uv run python scripts/static_check.py
uv run pytest --junitxml=reports/tests.xml
uv run python -m evals.run_evaluations
```

Static checks passed. The full pytest run executed **127 cases: 127 passed,
0 failures, 0 errors, 0 skipped**. Pytest wall time was 6.62 s; JUnit recorded
6.592 s. One Starlette TestClient deprecation warning was emitted.

| Coverage scope | Numerator / denominator | Result |
| --- | --- | --- |
| Statements across full regression | 1,296 / 1,360 | 95.29% |
| Branches across full regression | 274 / 310 | 88.39% |
| Combined executable opportunities | 1,570 / 1,670 | **94.01%** |

Coverage includes the enterprise runtime, ingestion, shared guards/chunking,
runner and artifact parser. The preserved pgvector provider/API/storage are
separate; eval/fixture builders and browser JavaScript are outside Python coverage.
Browser functionality is verified separately below.

All **105 independently labeled evaluation cases passed**: routing 42/42,
retrieval 19/19, answer quality 26/26, security 18/18. Each layer's failed-case
ID list was empty.

| Metric | Numerator / denominator | Result |
| --- | --- | --- |
| Intent accuracy | 42 / 42 | 100% |
| Recall@5 | 14 / 14 relevant documents | 100% |
| Fixed-slot Precision@5 | 14 / 70 slots over 14 positive queries | **20%** |
| Precision among actually returned unique documents | 14 / 23 | **60.87%** |
| MRR | 14 / 14 | 1.0 |
| Relevant retrieval coverage | 14 / 14 | 100% |
| Deterministic answer correctness | 26 / 26 | 100% |
| Exact citation validity | 6 / 6 | 100% |
| Extractive source support | 6 / 6 policy answers | 100% |
| Exact PTO fixture facts | 6 / 6 | 100% |
| Appropriate abstention/clarification/handoff/refusal | 11 / 11 | 100% |
| Labeled accepted facts | 7 / 7 | 100% |
| Security cases | 18 / 18 | 100% |

Unauthorized/outdated retrieval exposures and unsupported cited policy answers
observed: **0**. Precision@5 now uses a fixed five-slot denominator; the baseline
2.0 returned-result precision is retained as a separate metric. A short relevant
result set therefore has lower fixed-slot precision even if its first result is
correct. Neither metric is hidden. Negative retrieval cases check ACL/lifecycle
exclusion; authorized distractors may still rank and are rejected by the answer's
evidence threshold. Small English fixtures and exact support checks do not prove
comprehensive semantic groundedness, completeness or absolute security. The
optional live Qwen judge was not run.

Measured CLI evaluation reliability: **40/40** successful in-process requests,
p50 **3.072 ms**, p95 **3.619 ms**, p99 **3.821 ms**; **16/16** concurrent requests
succeeded. These are local synthetic measurements, not production SLOs.

Ranking/chunk experiments remained reproducible: TF-IDF and overlap at 120 and
600 characters produced identical quality metrics on these labels. The 120-character
configuration returned 40 chunks and 3,433 context characters across 19 queries;
600 characters returned 25 chunks and 4,064 context characters. No universal
ranking winner is established.

## Actual browser-triggered backend jobs

Every dashboard test button was clicked and its terminal browser result inspected.
Jobs used actual child Python processes and parsed their own JUnit/coverage files.

| Button | Job ID | Actual result | Coverage scope | Duration |
| --- | --- | --- | --- | --- |
| Unit | `870a6c69-ac0f-4bba-aa33-beca7b6093d8` | **52/52 passed** | Unit-only, **53.83%** | 1.818 s |
| Integration | `fd7da82a-6170-4804-86fb-969f6d07e772` | **49/49 passed** | Integration-only, **78.98%** | 4.035 s |
| Security | `2c55be60-9124-4a63-b2d2-f0b9d2f9d08a` | **10/10 passed** | Security-only, **72.87%** | 2.336 s |
| All evaluations | `bdfbdec8-942b-4fb1-9103-20a32a221758` | **127/127 tests, 105/105 eval cases, 13/13 gates passed** | Full regression, **94.01%** | 8.445 s |

All four jobs reported zero failed/skipped tests and a current matching source.
The full dashboard run separately measured p50/p95/p99 **3.144/3.872/4.055 ms**.
Partial-suite coverage is displayed as such; it is not represented as satisfying
the complete regression gate. The initial proposed unit-only 85% target remains
an explicit engineering gap. The configured CI gate enforces combined coverage
over all regression layers, and passed at 94.01%.

Saved safe job evidence: `reports/dashboard-jobs.json` and the portable
`docs/testing-layer-results.json`. Actual JUnit, coverage, manifests and evaluation
artifacts remain under each `reports/lab/<job-id>/`. Raw process logs are not
exposed through HTTP. The end-to-end automated test independently starts an
authenticated real unit subprocess and asserts canonical reports are unchanged.

## Core requests and data movement

The three core workflows were executed in the browser and again through the
signed mock Slack HTTP simulator against the final running source:

| Request as EMP100 | Actual result | Source / protected-call evidence |
| --- | --- | --- |
| How many PTO days do I have remaining? | `answered`: **12.5 days**, source date **2026-10-20** | SQLite `mock_workday` record → authorized mock client → typed record → exact response; `reports/live-pto-response.json` |
| What is our parental leave policy? | `answered`: exact approved US parental-leave procedure, **HR-PARENTAL-US v1.0** citation | Current inventory and document ACL before ranking; `reports/live-policy-response.json` |
| Show me EMP200's PTO balance. | `denied`: generic denial, empty facts/citations | Resource authorization denied, retrieval skipped, attempts 0; mock call assertions prove no protected method; `reports/live-denied-response.json` |

The live failure control also produced **upstream_503**, 3 attempts, no facts,
a failed retrieval stage and safe handling. Its trace does not claim a successful
record-validation/formatting step. Saved output: `reports/live-failure-response.json`.

Browser checks additionally confirmed invalid Slack signature rejection before
identity/source access, duplicate replay with no new protected read, matched YAML
rule IDs/config paths, and persona switching clearing prior data and operator
results. Employee test buttons were disabled; the backend independently rejected
missing/insufficient permissions and arbitrary suite/command/path inputs.

At 1280×900, document width was 1265 px and the source/rule inspectors used two
455.5 px columns. At 390×844, document width was 375 px: no horizontal overflow.
Temporary viewport overrides were reset. Screenshots:

- `docs/testing-layer-desktop.png`
- `docs/testing-layer-mobile.png`

## Source, ingestion and traceability

Runtime SQLite contained **7 employee identities**, **6 Workday records**,
22 registry versions, 16 indexed documents and 16 chunks. EMP100's stored row was
12.5 days dated 2026-10-20. A separate temporary-database integration test changes
that row to 10.75 and proves the answer changes to 10.75, ruling out a hardcoded
orchestrator balance. Unchanged fixture seed replay preserves the edit.

Fresh ingestion executed: **23 extracted, 16 indexed, 7 rejected**; repeat:
**16 unchanged, 0 new indexed**. Output: `reports/ingestion.json`. Existing version,
expiry, revocation, malicious source, immutable digest and removed-inventory tests
remain passing. Source corruption and mismatched adapter records are safely rejected.

Traceability reports **15 requirements, 23 acceptance/CSV rows, 68 test functions,
105 evaluation labels**, with no untested requirements, unmapped tests, missing
primary tests/files or unknown references. All **13 configured gates passed**.
The canonical pytest manifest confirms no source change during execution and
matches fingerprint:

`ade866e1b07c33c80c4ffcc0404b06491b19562669e06dfc540c190dca8c78e1`

Evidence: `reports/test-run.json`, `reports/evaluation.json`, `reports/release.json`,
`reports/traceability.json`, and portable `docs/enterprise-results.json`.

The earlier pgvector policy regressions were separately executed against the
dedicated test database: **61 passed, one warning, 1.85 s**. Reports were isolated
under `reports/legacy/` so they did not overwrite the enterprise evidence:

```sh
docker compose --profile test up -d test-db --wait
HR_TEST_REPORT_DIR=reports/legacy uv run pytest --no-cov \
  tests/test_vertical_slice.py tests/test_policies.py tests/test_providers_and_grounding.py \
  --junitxml=reports/legacy/tests.xml
```

## Fixes observed during this layer and remaining limits

The first expanded run stopped with 80 passes and one failure because the old
duplicate test compared the entire JSON response. Current-request timings/replay
diagnostics now intentionally differ; assertions preserve every business field,
correlation ID and protected-call count and additionally prove skipped replay
retrieval. Browser 503 testing also exposed an old breadcrumb claiming later
stages before they executed; it was corrected and covered by all fault profiles.
Both issues are resolved in the final 127-case run.

Open items: unit-only coverage below the proposed 85%, limited lexical precision
and semantic corpus coverage, no live optional model judge, no GitHub-hosted CI
execution, no Windows execution, and no new container rebuild for this layer.
Real SSO/Slack/Workday, production sandboxing, distributed coordination, retention,
TLS/encryption and owner approval remain in `operational_readiness.md`. A passing
local mock gate is not production certification.

The owned preview and test database service are stopped after QA. The existing
n8n/Qwen/policy services are preserved. Restart the lab with
`Start-Enterprise-HR.command`; its local URL is http://127.0.0.1:8811/.
