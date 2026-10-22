# Executed baseline

Prepared on 2026-10-22 (Asia/Seoul). Raw evidence filenames use UTC. Results below describe executed commands, not intended checks.

## Verified provenance

- Public repository: `https://github.com/debezium/debezium`.
- HEAD: `1397c912f32f48a6be513c481d9a1a6077dc8836`. The public issue explicitly reports this SHA as affected; the SHA was verified through GitHub and fetched directly with `git fetch --depth=1 origin <SHA>`.
- Original reporter test downloaded from the attachment URL in `pins.json`, SHA-256 `8dc8f19cca712c796d4b11b4b32a22282db5dcb0a76909a230c13c4ce5c22513`, copied unchanged into the upstream MySQL test package. It creates synthetic payloads and uses the upstream embedded engine and database fixtures.
- No later history, historical fix, or solution PR was retrieved. Final `git diff --exit-code` returned 0; the only untracked source file is the unchanged reporter test. A byte comparison and checksum verification succeeded at handoff.

## Executed results

| Check | Executed command | Observed result |
| --- | --- | --- |
| Docker engine | `docker version` | Available: Desktop 4.95.0, Engine 29.8.2, Linux ARM64 |
| Compose | `docker compose version` | v5.6.0 |
| Startup | `./scripts/record.sh startup docker compose up -d --wait mysql` | Exit 0, MySQL healthy |
| Toolchain | `docker compose run --rm -T runner -lc './mvnw -v; java -version'` (recorded) | Exit 0; Maven 3.9.12, Temurin 21.0.9+10-LTS |
| Server SQL | Version/binlog/GTID query (recorded under `database`) | 8.2.0, aarch64, log_bin=1, ROW, GTID OFF, FULL row image |
| Seed reconciliation | COUNT, DISTINCT, MIN, MAX on `testing.testing` (same capture) | 14 rows, 14 distinct IDs, range 1–14 |
| Dependency reactor | Full command in `evidence/20261022T105115Z-build-11203/command.txt` | Exit 0, all 22 modules built; 3m08s Maven time |
| Initial unit invocation | `./scripts/lab unit`, capture `20261022T105445Z-unit-11569` | Exit 1 before JUnit: missing local `debezium-ide-configs:3.7.0-SNAPSHOT` plugin artifact |
| Support artifacts | Command in `evidence/20261022T105556Z-build-support-11674/command.txt` | Exit 0; original support/ide-configs, support/checkstyle, support/revapi built from the same SHA |
| Targeted unit tests | `./scripts/lab unit`; online capture `20261022T105635Z-unit-11763`, offline capture `20261022T110047Z-unit-12281` | Both exit 0; 4 passed, 0 failed, 0 errors, 0 skipped per run |
| Existing pipeline smoke | `./scripts/lab smoke`; online capture `20261022T105723Z-smoke-11847`, offline capture `20261022T110053Z-smoke-12346` | Both exit 0; 4 unit tests passed, integration suite: 3 passed, 2 skipped, 0 failed/errors |
| Reporter workload, run 1 | `./scripts/lab challenge`; capture `20261022T105905Z-challenge-12057` | Exit 1; 1 integration assertion failed, 0 test errors; consumer observed 14,546 distinct IDs, 455 expected IDs missing |
| Reporter workload, run 2 | `./scripts/lab challenge` in offline mode; capture `20261022T110140Z-challenge-12466` | Exit 1; 1 integration assertion failed, 0 test errors; consumer observed 14,552 distinct IDs, 449 expected IDs missing |
| Independent source reconciliation | Recorded SQL query in `20261022T110325Z-source-rows-both-12674/command.txt` | Exit 0; both workload tables contain 15,001 committed rows and 15,001 distinct IDs, range 1,000,001–1,015,001, one sentinel each |
| Resolved dependency tree | Recorded offline `dependency:tree`, capture `20261022T105959Z-dependency-tree-12143` | Exit 0; tree saved under `evidence/setup/dependency-tree.txt` |
| Dependency fingerprints | SHA-256 generation and verification, capture `20261022T110048Z-dependency-hashes-12294` | Exit 0; 2,531 Maven JAR/POM files fingerprinted; prepared repository cache approximately 505 MB |
| Final integrity and isolation | Capture `20261022T110325Z-final-integrity-12690`; Bash syntax and Compose config validation | Exit 0; exact SHA, no tracked source diff, unchanged reporter test, MySQL healthy, no published host ports |
| dbt validations | Not executed | Not applicable: selected workflow has no dbt project |

Startup log: `evidence/setup/mysql-startup.log`. Each recorded run contains command, output, exit status, and start/end timestamps.

The integration smoke selected `ConnectionIT` and `MySqlConnectorIT#shouldConsumeAllEventsFromDatabaseUsingSnapshot`. The executed snapshot test includes normal snapshot validation and delivery after connector restart. `ConnectionIT.shouldConnectToDefaultDatabase` and `ConnectionIT.shouldConnectToEmptyDatabase` are annotated `@Disabled` upstream; they are skipped, not passed. The targeted unit classes are `MySqlConnectorConfigTest` (3 tests) and `MySqlConnectorTest` (1 test).

## Locally observed investigation symptom

Both unchanged reporter-test runs reached the data-completeness assertion and failed there after the sentinel was consumed. This is a locally reproduced source/consumer discrepancy in 2 of 2 attempts under these conditions, not a diagnosis or a promise of deterministic reproduction on every platform. Missing counts differed between runs. Do not require the historical report's exact count or range.

The original reporter assertion checks missing expected identities. Full physical-duplicate and unexpected-identity reconciliation has not been performed. Process shutdown completed normally in both logs; that does not establish data correctness. Cause analysis is deliberately left to the learner, with no application repair attempted.

The retained source schemas are `connector_test_ro_1jt1vw7` (run 1) and `connector_test_ro_kp6w93` (run 2). The independent read-only query was:

```sql
SELECT 'connector_test_ro_1jt1vw7' AS source_schema,
       COUNT(*) AS committed_rows, COUNT(DISTINCT id) AS distinct_ids,
       MIN(id) AS first_id, MAX(id) AS last_id, SUM(id=1015001) AS sentinel_rows
FROM connector_test_ro_1jt1vw7.keepalive_repro
UNION ALL
SELECT 'connector_test_ro_kp6w93', COUNT(*), COUNT(DISTINCT id),
       MIN(id), MAX(id), SUM(id=1015001)
FROM connector_test_ro_kp6w93.keepalive_repro;
```

## Setup blockers and disclosed remedies

The initial cold build (`20261022T104052Z-build-10412`) was stopped deliberately with a targeted `docker stop`, exit 143, while resolving dependencies at module 8/22. This is an operator interruption, not an application/test failure. Cache files continued to advance; thread evidence showed Maven dependency resolution, and direct HTTP probes returned Central 200 and Confluent 404 for an ordinary Central artifact, with the latter taking about 1 second. `maven-settings.xml` now puts the existing Central repository first. The complete build then succeeded with the original versions and retained cache. Diagnostic capture: `evidence/20261022T104732Z-dependency-progress-10960/`.

The first unit invocation established a setup blocker: the quick connector-only build omitted the upstream formatting-support JAR, but the normal profile resolves that plugin dependency even with formatting skipped. It exited 1 before any unit test ran. Building the original three support artifacts from the pinned checkout resolved this blocker; subsequent unit and integration controls executed successfully. Future `./scripts/lab build` includes those artifacts explicitly. A subsequent attempted stop found that the already-failed test container had been removed; it changed no resources.

## Disclosed environment choices and limits

The host has no Java runtime. A digest-pinned JDK/Maven image provides Java 21 and runs the checkout's Maven wrapper. Its preinstalled Maven 3.9.11 is not used.

The selected workflow uses Debezium's embedded integration-test runtime, as in the reporter's reproduction. No Kafka, warehouse, lineage server, observability service, or dbt layer was added. SQL probes validate MySQL settings and fixtures; they do not establish consumer completeness.

Compose starts the upstream-supported official `mysql:8.2` alternative with the original read-only server configuration and seed SQL. Upstream Maven's automatic Docker lifecycle is disabled and the database hostname is set to the Compose service name. No Docker socket is mounted. The test platform is native ARM64; upstream's default Docker platform is AMD64. Workload timing can differ. The historical failure count is not assumed to hold here.

The quick reactor build skips regular unit/integration tests and QA profile checks, but the upstream separately configured ArchUnit execution still runs during the build; its results are in the raw build log. Focused test commands explicitly exclude ArchUnit, formatting, and Checkstyle. The full cross-connector suite is outside this environment's scope. Dependency versions are inherited from the pinned POMs, including binlog client 0.41.0. This is a historical SNAPSHOT source build, so retain the local reactor artifacts and Maven cache and avoid dependency upgrades.

Normal unit, smoke, and challenge helpers now use Maven offline mode. All three were executed in that mode; the unit and smoke controls passed and the challenge reproduced the discrepancy. After a cache loss, run `up`, `build`, then `warmup` to repopulate the same dependencies and test plugins. `warmup` uses the already-executed online smoke command. The fingerprint manifest describes the prepared cache; byte-identical metadata from fresh SNAPSHOT JAR builds is not claimed.

Upstream model, logging, and plugin warnings remain in the raw logs. The offline dependency-tree goal warned about uncached descriptors for unused release/legacy-formatting plugins but exited 0 and wrote the tree; no release or legacy-formatting goal was run. No setup blocker remains for the documented current commands. The application discrepancy is preserved and its cause is uninvestigated.

## Methodology preparation update, 2026-10-22

This documentation-only follow-up added INVESTIGATION_LOG.md, independent process/correction review records, and explicit source/applicability registers. The actual Standardized SRE Methodology attachment was not available in the supplied file references or located by local document searches; its path was requested. Exact methodology phase mappings and checkpoints remain unassigned, with no methodology-completion claim.

Only read-only repository identity, working-tree, and original-test checksum checks were performed during this follow-up. HEAD remained the pinned SHA, the tracked diff remained empty, and both copies of the reporter test retained SHA-256 `8dc8f19cca712c796d4b11b4b32a22282db5dcb0a76909a230c13c4ce5c22513`. No pipeline, workload, root-cause experiment, or correction was executed in this follow-up. Earlier results above remain preparer evidence and are not learner process credit.
