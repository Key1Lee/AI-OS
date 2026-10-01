# Artifact research and implementation choices

Reviewed public primary documentation on 2026-10-02. This research informs the
adapter contract; it is not learner competency evidence.

- [dbt manifest](https://docs.getdbt.com/reference/artifacts/manifest-json):
  resources, sources, tests, exposures, metrics and dependency declarations.
  The adapter uses explicit `depends_on.nodes`, retains conflict information,
  and recognizes manifest resource subsets v7–v12. Older raw SQL names are read
  as fallbacks. It does not claim exhaustive schema compatibility.
- [dbt run results](https://docs.getdbt.com/reference/artifacts/run-results-json):
  execution results are attached by `unique_id`; a partial run does not establish
  the health of unexecuted nodes. Operation and individual test/build results are
  kept separate. Compile success does not prove a model was built.
- [dbt catalog](https://docs.getdbt.com/reference/artifacts/catalog-json): optional
  catalog-reported column types enrich schema declarations; mismatches are
  visible rather than silently discarded. Nullability stays unknown without
  an explicit declaration.
- [source freshness](https://docs.getdbt.com/reference/artifacts/sources-json) and
  [freshness artifacts](https://docs.getdbt.com/reference/artifacts/freshness-json):
  optional recorded freshness is separate execution evidence. Fresh sources do
  not establish downstream model correctness.
- [dbt schema definitions](https://github.com/dbt-labs/schemas.getdbt.com): primary
  reference for artifact versions. This small release uses shape validation for
  supported fields rather than introducing a network/schema-fetch dependency.

No production metadata connection, dbt command or AI service is needed at runtime.
SQLGlot, SQLFluff, precise column mappings, natural-language graph queries and
additional adapters remain subsequent slices after this one is independently
verified. Existing React/TypeScript, FastAPI, SQLite and DuckDB dependencies are
reused. Accessible HTML graph nodes with SVG edges avoid another package.
