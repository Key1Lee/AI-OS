# Data Observability extraction plan

Authorization: the 2026-10-02 structural-refactoring request and explicit destination
`/Users/key/_AI-OS/projects/Data Observability System`. Both projects lack Git history;
the destination is empty. Independent baseline: **146 Python tests passed**.

## Migration map (recorded before source changes)

| Action | Source → destination |
| --- | --- |
| MOVE | `data_system_map/` → sibling `src/data_system_map/` as an installable local package; keep Python import names and serialized contracts |
| MOVE | generic graph/dbt/service tests → sibling `tests/observability_tests/` |
| MOVE | generic import/security/incident regressions → sibling `tests/regression/`; retain trainer-policy regressions here |
| MOVE | demo fixtures and generator → sibling package `data_system_map/demo/`, packaged for independent installation |
| MOVE | graph, node details, map styles, generic response types → sibling `web/src/` |
| SPLIT | `apps/api/data_map.py` → generic API router/context in Observability, trainer context and investigation routes in Toptal |
| SPLIT | `DataMap.tsx` → generic map view with consumer extension slots, Toptal wrapper for modes/notebook/history |
| SPLIT | `types.ts` → generic contracts in Observability, investigation/answer/rubric types in Toptal |
| KEEP | `trainer/data_map/`, original exercise bank, learner databases, canonical assessment records and investigation storage |
| MOVE | observability documentation/screenshots → sibling docs; retain trainer policy/integration documentation here |
| CUT OVER | existing metadata SQLite profile → sibling data folder after stopping the owned local process; preserve snapshot identities and bytes, without schema migration |

## Contracts and execution

Preserve `/api/map` routes, JSON contracts, token/origin behavior, error codes,
ordering, bounded graphs, demo evidence, snapshot identity, draft revisions,
idempotency, assessment hiding and the existing `/map` trainer experience.
Toptal consumes public service methods and a context-configured generic router;
the generic system imports no trainer modules or learner policy. React uses
consumer-supplied controls/slots and an injected request client. One canonical
implementation exists for graph algorithms, parsing, API exploration and generic UI.

Use editable local Python packaging and Vite/TypeScript aliases to the sibling UI.
Add an independent local app/build in the new project. Networking between the
projects is not required. Generic storage configuration is `OBSERVABILITY_DB`;
explicit test profiles remain isolated. No production or external actions.

Recovery is moving canonical source files and the stopped metadata file back,
then restoring the consumer import/build configuration. Capture pre-cutover hashes
and preserve learner records; do not copy or reset evidence to fake a migration.

Run engine, trainer integration, boundary/contract, full backend, lint/typecheck,
both frontend builds, demo generator and existing 11 browser checks. Add an
independent-app contract smoke check. Reuse the same single Verification Agent
for adversarial preservation checks; completion requires its PASS.

SQLGlot, SQLFluff, column lineage, live AI and runtime adapters were not implemented
in the source baseline and remain later work. This refactor does not add them.

## Implemented state

The package is installed from sibling `src/data_system_map`; source API and UI
are consumer adapters. Generic tests live under `tests/observability_tests`.
Trainer policy and its integration/browser tests remain here. Metadata cutover
completed with bytes/identities preserved, and the normal trainer was restarted.
See the sibling `docs/migration.md`, `docs/database-cutover.json` and
`docs/verification.md` for current evidence and recovery. Baseline JSON artifacts
and algorithms remain unchanged; packaged README paths were updated.

Final independent verification: **PASS** from the exactly one reused helper,
`/root/verification_agent`. Combined Python suite: 152 passed; independently
installed generic suite: 35 passed. Browser suites: 11 trainer + 2 standalone
passed. Both builds/typechecks/demo checks passed, and the pre-migration full
OpenAPI and scoped map CSS contracts match. The helper report lives in the sibling
`docs/verification-agent.json`; assessment hiding and mode transitions were
verified on disposable profiles.
