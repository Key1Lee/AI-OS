# Public curriculum research — 2026-10-01

Inspection date uses the user's Asia/Seoul build date. These are public sources,
not official competency weights or confidential interview questions.

| Source | Relevant insight | Design implication |
|---|---|---|
| [DataDriven AE overview](https://datadriven.io/analytics-engineer-interview), page updated 2026-07-27 | Public publisher guidance emphasizes SQL, modeling, dbt and metric definitions. Its interview prevalence claims are publisher claims, not independently verified hiring policy. | Original production scenarios; executed SQL plus a separate reasoning rubric. No copied questions or paid content. |
| [Toptal public screening](https://www.toptal.com/top-3-percent), inspected 2026-10-01 | Describes skill review, live problem solving, communication and practical projects; process can vary. | Practice those skills without claiming to reproduce a confidential screen or predict admission. |
| [dbt incremental models](https://docs.getdbt.com/docs/build/incremental-models), inspected 2026-10-01 | Grain, unique keys and strategy govern update behavior; NULL keys and duplicate keys need care. | Future labs must test replay, duplicates, backfills and final materialized state. |
| [dbt unit tests](https://docs.getdbt.com/docs/build/unit-tests), inspected 2026-10-01 | Unit tests evaluate model logic, including incremental branches, rather than proving the final merge result. | Use actual successive builds alongside unit tests for incremental labs. |
| [DuckDB security](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview), inspected 2026-10-01 | SQL can access files, extensions and network. Configuration is defense in depth; OS isolation is required for untrusted input. | Separate worker, locked configuration and OS sandbox; fail closed on unsupported hosts. |
| [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), inspected 2026-10-01 | Typed structured output is supported; refusal/error handling still matters. | Configurable Astra interface, strict schema, no direct mastery control, mocked tests. |

The initial twelve executable problems are original synthetic contracts. No
source answer, proprietary exercise or private bank was imported.

