# Executed baseline — 2026-10-22 UTC

## Provenance and preservation

FACT: [n8n issue #34359](https://github.com/n8n-io/n8n/issues/34359) was retrieved from GitHub. Its report timestamp is 2026-07-16 15:02:50 UTC. It does **not** identify a release or commit. This link can contain spoilers; reading it is unnecessary for the exercise.

FACT: GitHub's default-branch commit query at/before that timestamp returned [`50c3d88af56ebb869f76f13a2417c528d90ffd4c`](https://github.com/n8n-io/n8n/commit/50c3d88af56ebb869f76f13a2417c528d90ffd4c), committed at 2026-07-16 14:46:02 UTC. The API response is preserved in `evidence/setup/historical-commit-metadata.json`. The exact query and local Git verification are in `evidence/setup/source-verification.json`.

The checkout was obtained using:

```bash
git -C source/n8n init
git -C source/n8n remote add origin https://github.com/n8n-io/n8n.git
git -C source/n8n fetch --depth=1 origin 50c3d88af56ebb869f76f13a2417c528d90ffd4c
git -C source/n8n checkout --detach FETCH_HEAD
```

FACT: This unmodified historical revision exhibits the reported public class of correctness failure in two local runs of the real Agent V3 entry point. Thus it is a locally verified affected pin for this lab. This does not establish which exact SHA the reporter used, nor a root cause. No later history, maintainer regression, or historical fix was imported. New fixture and environment code live outside the upstream checkout.

The original report, Debezium checkout/test fixture, configuration, scripts, documentation, and old evidence were hashed before extension. `evidence/setup/preservation-after.json` records the final comparison. Only the parent's START_HERE navigation receives the requested two-line addition. Unrelated services remain running. No old challenge was rerun.

## Versions / execution boundary

| Item | Actual value |
| --- | --- |
| Host / runtime architecture | macOS ARM64 / Linux ARM64 container |
| Source release / selected node version | 2.31.0 / Agent V3 typeVersion 3 |
| Node / pnpm | 22.22.0 / 10.32.1, executed in container |
| Upstream engine requirements | Node >=22.22; pnpm >=10.22.0; packageManager pnpm@10.32.1 |
| Vitest | 4.1.9, shown by executed tests |
| Base image | `node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94` |
| Built image ID | `sha256:584bc340fbb9494678941cf112ade5bcc860c6802678bd42501870d81adb7c43` |
| Original pnpm-lock.yaml SHA256 | `bca5f41de75ead3f54df983a9dbb275b92799b9266406869aea8eb36fa942d36` |

Exact pins, fixture hash, and reproduction evidence paths are in `pins.json`. Host Node 24 and pnpm 11 are not used for this track's builds/tests.

## Actual commands and results

Commands were run from this track's root. Every run below has its exact expanded command, timestamps, full output, and true exit code in the named evidence directory.

| Command / executed operation | Result | Evidence directory under `evidence/` |
| --- | --- | --- |
| `./scripts/lab image` | PASS, pinned Node image + pnpm prepared | `20261022T123155Z-image-17202` |
| `./scripts/lab install` | PASS, frozen lockfile, filtered workspace dependencies, lifecycle scripts disabled | `20261022T123210Z-install-17286` |
| `./scripts/lab versions` | PASS, v22.22.0 / 10.32.1 | `20261022T123529Z-versions-18045` |
| Initial scoped `build:unchecked` dependency build | PASS, 24 tasks; prerequisite coverage expanded below | `20261022T123530Z-build-18035` |
| `./scripts/lab unit` | PASS: **71 tests, eight files**, no skipped tests in this selection | `20261022T123638Z-unit-18424` |
| nodes-base `tsc --build tsconfig.build.cjs.json --noCheck` | PASS, public-node metadata prerequisite generated | `20261022T123751Z-build-nodes-base-18745` |
| json-schema-to-zod original `build:unchecked` | PASS, missing package entry generated | `20261022T123922Z-build-schema-19294` |
| Final `./scripts/lab build` | PASS, 25 Turbo tasks (24 cached), nodes-base compiler + alias step; exit 0 | `20261022T124518Z-build-19914` |
| `./scripts/lab run single-hr` (final harness) | PASS: one business test; one completion, one effect; contract checks true | `20261022T124148Z-business-single-hr-19662` |
| `./scripts/lab run single-survey` (final harness) | PASS: one business test; one completion, one effect; contract checks true | `20261022T124153Z-business-single-survey-19687` |
| `./scripts/lab run pair` | **FAIL**, one business test, exit 1; node runs to completion, contract not satisfied | `20261022T124157Z-business-pair-19652` |
| `./scripts/lab run pair` repeated unchanged | **FAIL**, same business assertion and reconciliation signature, exit 1 | `20261022T124218Z-business-pair-19783` |

FACT: Both combined runs produced two terminal outputs and two committed mock service effects, with zero API authorization denials and no node execution exception. The aggregate business contract was false in both. Per-request evidence and individual assertions are available in their `artifacts/reconciliation.json`, model transcripts, node histories, and effect ledgers. No causal localization, correction, or hypothesis experiment was performed.

## Setup failures and disclosed adaptations

These failures preceded the final usable harness. They are not application-defect reproduction evidence and were not deleted:

| Failed run | Observation | Environment/harness correction |
| --- | --- | --- |
| `20261022T123651Z-business-single-hr-18523` | Zero tests: setup-file path resolved under the external harness root | External config now replaces the setupFiles array with the upstream setup file's absolute container path; upstream config untouched |
| `20261022T123716Z-business-single-hr-18655` | Zero tests: missing compiled nodes-base property metadata | Generate original nodes-base compiler outputs; do not stub the imported application module |
| `20261022T123905Z-business-single-hr-19161` | Zero tests: missing compiled json-schema-to-zod entry | Run that package's original build script and include it in reproducible setup |
| `20261022T123947Z-business-single-hr-19434` | One test failed at iteration bound; fixture model did not recognize n8n's JSON-array tool result envelope | Correct the fixture decoder to consume arrays, retaining authentic n8n responses and history. Later single-request controls pass |

Earlier controls `20261022T124042Z-business-single-hr-19544` and `20261022T124113Z-business-single-survey-19605` also passed. The final controls additionally include the model-boundary identity audit and failure-artifact capture. The final source tracked diff remains empty.

Dependency installation deliberately used `--ignore-scripts` to avoid unrelated native builds and repository prepare hooks. Prerequisites use upstream `build:unchecked` / `--noCheck` compilation, not a full typecheck. This is disclosed scope, not a claim that the entire monorepo builds cleanly. The public node is loaded directly from original TypeScript by the upstream test runner; no alternate agent implementation is substituted.

## Limitations / blockers

No unresolved blocker prevents this package-level investigation. The full n8n app/UI was not started; full monorepo tests, lint/typecheck, live-model behavior, SQL/dbt, persistent memory, durable restarts, real IAM, scheduler/queue behavior, and production rollout were not exercised. Native optional dependencies were not built. These must not be reported as passed.

The local fixture's identity checks and per-run idempotency ledger are supporting external-system behavior. They do not prove production authorization, durable deduplication, or n8n restart recovery. Negative authorization and recovery experiments remain learner work; the baseline did not conduct them.

This track follows the exact eight-phase sequence explicitly provided in the extension request, using the unchanged Deep Research methodology section and Google SRE as supporting sources. It does not claim integration of the earlier separate Standardized SRE Methodology attachment whose source was unavailable in the original track.
