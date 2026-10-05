# Extraction and recovery — 2026-10-02

Source: `/Users/key/_AI-OS/projects/Toptal-Testing`.
Target: `/Users/key/_AI-OS/projects/Data Observability System` (initially empty).
Neither directory has Git history. The concise migration map was recorded in the
trainer's `docs/data-observability-migration.md` before modifying source files.

## Ownership and compatibility

Moved the `data_system_map` package into `src/`, packaged the original demo and
its generator, and moved engine/dbt/graph/incident/security tests. Split the mixed
API into a generic router and trainer context. Split React map rendering, generic
contracts, request client, widgets and styles from modes/notebook/history.
Existing Python import names, `/api/map` routes, DTOs and trainer `/map` UI remain.
Scoring, disclosure, candidate actions, drafts and learner stores stay in Toptal.

Normal trainer launches use the sibling `data/observability.db`. Its investigation
profile stays `Toptal-Testing/data/data-map-training.db`. Explicit `AE_TRAINER_DB`
profiles keep temporary sibling map/action databases for isolation, independently
of default `OBSERVABILITY_DB`. For normal launches the generic environment override
is honored. No schema conversion, identity regeneration or record reset occurs.

## Cutover

Stop the owned trainer process before moving metadata. Confirm no file handles
remain, record database and snapshot hashes, and preserve a stopped-profile backup.
Move the metadata file and any sidecars into the target; verify byte hashes,
integrity, normalized bodies, system pointers and snapshot identities. SQL and
investigation records stay in the source project. The cutover record is
`docs/database-cutover.json`; it contains hashes/counts/identities, no candidate
answers. Restart the trainer using the moved package and new build.

## Recovery

Stop local app processes first. The source retains
`.cache/observability-extraction-before.tar.gz` as a code/config recovery snapshot;
`docs/migration-baseline.json` records hashes. A stopped metadata backup lives at
`.cache/observability-profile-before/` in the trainer. Do not overwrite newer
learner evidence with a baseline backup.

For rollback before new writes, restore moved code/config from that archive,
restore shared foundational rules from `web/src/foundation.css` into the trainer
stylesheet and remove its new foundation import/alias; move the stopped metadata
profile and sidecars back to
`Toptal-Testing/data/data-system-map.db`, and restore the original trainer default
path. Remove the new editable dependency and restore the original UI build.
After later metadata writes, move the current stopped profile back instead of
replacing it with the backup. Leave SQL/investigation/canonical registers intact.

## Evidence

Baseline: 146 passing Python tests. Core graph/contracts/dbt/security/repository
and four JSON fixture hashes match the captured source baseline. Added six ownership,
independent-package, contract/projection and configuration tests. Frontend and
backend checks, standalone package execution outside either checkout, original
commerce flow and existing trainer browser scenarios are recorded separately in
`docs/verification.md`. The sole helper agent must return PASS before completion.

Prior implementation reports in `docs/initial-implementation/` are historical.
Their old paths and combined ownership describe the baseline, not current setup.
SQL analysis, column lineage and AI were already deferred; extraction adds none.
