# Migration verification — 2026-10-02

Final outcome: **PASS**, independently verified by the single
`/root/verification_agent`. This records implementation and preservation checks.
No learner mastery or successful candidate attempt is claimed.

| Check | Observed result |
| --- | --- |
| Baseline helper run | 146 Python tests passed before extraction |
| Toptal `make test` | 152 passed (23.31 s); all 146 baseline cases retained plus six boundary tests |
| Independent `make setup` | Own virtual environment, editable package, npm clean install and UI build passed |
| Independent `make test` | 35 passed (2.69 s), without trainer dependencies |
| Both `make lint` | Python compilation / TypeScript typechecks passed; trainer launcher syntax passed |
| Both production UI builds | Passed |
| Trusted demo checks | Both passed; fixture output matches checked-in artifacts |
| Existing Toptal browser suite | 11 passed (25.3 s), final build, including SQL, learning, assessment, drafts and multi-tab recovery |
| Independent browser suite | 2 passed (1.9 s); incident evidence, inert SQL, import, keyboard stages, narrow/light layout and absence of learner UI |
| Full trainer OpenAPI | Exact baseline match: 46 paths / 25 map paths, identical serialized contract hash |
| Map CSS preservation | Baseline selectors, declarations and media scopes match across the two extracted stylesheets |
| Metadata cutover | Byte hashes, system/snapshot identities and row digests preserved; integrity `ok`; SQL/investigation/canonical records unchanged |

The original Starlette/httpx deprecation warning remains. The trainer's existing
Monaco bundle triggers Vite's large-chunk warning; neither is a test failure.
Generic build has no such bundle. Package/runtime adapters import no trainer,
scoring or rubric modules. New tests assert public facade consumption, standalone
package execution outside both checkouts and authoritative trainer projection.
Historical first-slice SQL analysis/column-lineage limitations remain unchanged.

The sole helper independently reran 152 Python tests, 35 standalone tests, both
builds/typechecks/demo checks, 11 trainer browser scenarios (25.5 s), two standalone
browser scenarios (1.9 s), all 12 graph query variants and all three incident
projection routes under assessment. It reproduced exact OpenAPI and 408 scoped
CSS rule entries, and checked a focused learning → assessment → learning
transition cleared SQL/diagnostic panels and restored overview. It returned PASS;
its full evidence report is `verification-agent.json`. No real learner mutation
endpoints were used. The trainer was
restarted successfully; read-only default-profile smoke retained 12 exercises,
five stages, snapshot identity and unchanged SQL/investigation file hashes.
Fourteen baseline code/fixture/register files match captured hashes (the packaged
demo README intentionally updates its generator path). Recovery and preservation hashes are in `migration.md` and
`database-cutover.json`. Actual default learner APIs are checked read-only.
