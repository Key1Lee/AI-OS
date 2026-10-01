# dbt lab implementation boundary

Phase 3 is planned. This release does not execute dbt or claim dbt competence
from SQL results. No dbt package has been installed for an unimplemented runner.

The planned runner needs isolated projects, path-validated model/YAML edits,
frozen profiles and seeds, process time/output limits and a real sandbox before
accepting Jinja or macros. Python/Jinja can execute host code; SQL-only DuckDB
settings are insufficient. Execute parse/build/test and capture artifacts.
Successive incremental builds must verify final materialized state, replay,
late arrivals and backfills, not merely compare compiled SQL or unit tests.

Relevant sources are recorded in [public curriculum research](research/2026-10-01-public-curriculum.md).
