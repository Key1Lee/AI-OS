# Local runbook

Run every command from `/Users/key/_AI-OS/projects/data-debugging-lab`. Do not run two test commands concurrently: the upstream tests share local state and report paths.

This is a command reference, not a methodology phase sequence. Select commands through the learner's investigation decisions and the actual governing methodology; record predictions, executions, and evidence in INVESTIGATION_LOG.md. The reviewer does not automatically execute these commands or the full investigation. Methodology-specific mapping is pending receipt of the actual document.

| Purpose | Command |
| --- | --- |
| Start or resume MySQL | `./scripts/lab up` |
| Compile/install the connector reactor and upstream support artifacts; regular unit/integration tests skipped | `./scripts/lab build` |
| Populate a fresh cache online by running the same upstream smoke controls | `./scripts/lab warmup` |
| Targeted existing connector unit tests | `./scripts/lab unit` |
| Existing JDBC and snapshot/restart pipeline smoke tests | `./scripts/lab smoke` |
| Original reporter workload and reconciliation | `./scripts/lab challenge` |
| MySQL server logs | `./scripts/lab logs` |
| Containers, exact checkout SHA, working tree | `./scripts/lab status` |
| Interactive local SQL | `./scripts/lab sql` |
| JDK/Maven shell | `./scripts/lab shell` |
| Stop this project's containers; retain both volumes | `./scripts/lab down` |

`scripts/lab` contains the full Maven commands. All builds invoke the source-pinned `./mvnw`, not the image's Maven binary. Runtime images are pinned by OCI digest in `compose.yaml`. Upstream dependency versions come from the pinned POMs; no versions are overridden. Automatic source formatting is disabled to preserve the checkout. ArchUnit and code-style checks are excluded from the focused test commands; they are not part of the claimed baseline.

The lab-local `maven-settings.xml` puts the existing Maven Central repository first. A measured cold-build delay came from probing Confluent before Central for ordinary artifacts. Confluent remains available for its own artifacts; no upstream POM or dependency version was changed. The initial interrupted build and the subsequent run are both retained in `evidence/`.

The build explicitly includes `support/ide-configs`, `support/checkstyle`, and `support/revapi`. The connector-only quick reactor omits them, while normal-profile test commands need the plugin artifacts even when their checks are skipped. They are built from the same SHA, with no replacement artifacts or source patches.

Normal `unit`, `smoke`, and `challenge` commands run Maven offline. For a lost cache, run `up`, `build`, then `warmup`; warmup runs the same smoke controls with downloads enabled and pins unchanged. `evidence/setup/dependency-tree.txt` records resolved versions, and `maven-artifacts.sha256` fingerprints the prepared Maven JARs/POMs. These hashes describe this cache, including locally built SNAPSHOT artifacts; a fresh source build is not claimed to produce byte-identical JAR metadata.

## Evidence and reports

For each recorded command, inspect `evidence/<UTC>-<label>-<pid>/command.txt`, `output.log`, `exit-code.txt`, `started.txt`, and `finished.txt`. A failing command returns its original exit status through the logging wrapper.

JUnit XML and text reports live under:

```text
source/debezium/debezium-connector-mysql/target/surefire-reports/
source/debezium/debezium-connector-mysql/target/failsafe-reports/
```

A later test can replace these files. Archive reports alongside the relevant raw log before rerunning. MySQL retains each run's uniquely named synthetic database until the local volume is removed.

The recording helper automatically copies newly written Surefire/Failsafe report files and captures MySQL logs after unit, smoke, and challenge commands, including on failure.

## SQL probes

```bash
./scripts/lab sql 'SELECT VERSION(), @@log_bin, @@binlog_format, @@gtid_mode, @@binlog_row_image;'
./scripts/lab sql 'SELECT COUNT(*), COUNT(DISTINCT id), MIN(id), MAX(id) FROM testing.testing;'
./scripts/lab sql "SELECT TABLE_SCHEMA, TABLE_NAME FROM information_schema.tables WHERE TABLE_NAME='keepalive_repro';"
```

Use the actual schema returned by the final query to inspect the relevant workload. Reconcile keys, counts, transaction membership, and declared filters. Do not change replication settings or delete a run's data while collecting evidence. The fixtures use public constant passwords, including root `debezium-rocks`, test writer `mysqluser/mysqlpw`, and test capture account `cloud/cloudpass`. These accounts have no meaning outside this isolated lab.

## Setup troubleshooting

If Docker is unavailable, start Docker Desktop and rerun `docker version`, then `./scripts/lab up`. If MySQL is unhealthy, preserve `./scripts/lab logs` before changing anything. If Maven fails before tests start, record the artifact, network response, or compiler error; do not call it an application failure.

The fixture configuration and seed SQL are mounted read-only from the checkout. The Maven Docker plugin is disabled because Compose owns the database, and `docker.host.address=mysql` points tests to that service. No Docker socket, host credentials, or host Maven settings are mounted. The official MySQL image is an upstream-supported alternative; the original image is not used. This ARM64 environment differs from upstream's default AMD64 test platform, so timing-dependent results require local validation.

Never use `docker system prune`, global container cleanup, or commands against external databases. `./scripts/lab down` preserves the local database and dependency cache. Volume deletion destroys local evidence and is intentionally absent from the helper.
