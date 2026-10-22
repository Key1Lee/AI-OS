# Start your Debezium investigation

Additional independent track: [Enterprise request reliability — n8n AI Agent V3](challenges/n8n-ai-agent-v3/START_HERE.md).

You are investigating a genuine public defect in [Debezium at the pinned commit](https://github.com/debezium/debezium/tree/1397c912f32f48a6be513c481d9a1a6077dc8836). The application is unpatched. All data and credentials belong to disposable local test fixtures.

To start the prepared local service:

```bash
cd /Users/key/_AI-OS/projects/data-debugging-lab
./scripts/lab up
```

The checkout and build cache are already prepared on this computer. The unit, smoke, and challenge commands are listed in RUNBOOK.md; select and record them as needed by the actual methodology and your investigation decisions. They do not define a required phase order. After losing the build artifacts or Maven cache, `./scripts/lab build` and `./scripts/lab warmup` restore dependencies and execute the existing setup controls. Normal unit, smoke, and challenge runs use Maven offline mode to retain the prepared versions. Docker Desktop must be running. No host Java or Maven installation is needed.

Read `BASELINE.md` for actual setup results and limitations. A nonzero challenge exit is evidence to inspect, not permission to repair anything. Each execution writes its command, output, timestamps, and true exit code into `evidence/`.

## What is running

```text
JUnit workload -> MySQL 8.2 committed synthetic rows -> binary log
             -> real Debezium MySQL connector -> embedded test engine
             -> SourceRecord consumer -> identity reconciliation assertions
```

MySQL is the only persistent service. Each Maven invocation runs in a temporary JDK 21 container. The test engine is Debezium's existing embedded runtime; Kafka is unnecessary for this reported workflow. The original configuration, seed SQL, Maven reactor, JUnit, and Failsafe are reused. No dbt project or SQL transformation layer exists in this workflow.

## Your first task

Use your actual Standardized SRE Methodology as the governing protocol once its document is available. Its source has not yet been identified, so the phase mapping and methodology-specific checkpoints are explicitly pending in CHALLENGES.md and EVALUATION.md. Do not treat the existing challenge order or Deep Research report as a substitute methodology.

First record the governing document and the applicable exact source requirements in INVESTIGATION_LOG.md. The phase mapping is awaiting that source. The existing contract/reconciliation challenge remains available for the applicable phase: define expected source/consumer behavior, preserve each run's evidence, and independently check identities. Connection status, a sentinel, and an aggregate count have different evidentiary limits.

Copy INVESTIGATION_LOG.md for your run. Record expected versus observed behavior, source and consumer evidence, what the existing tests establish, your competing hypotheses, and your experiment predictions before execution. Identify provided baseline evidence separately from your own measurements. Do not fix the application yet.

Start with `CHALLENGES.md`. Use `RUNBOOK.md` for commands. `EVALUATION.md` defines measurable completion criteria without giving the answer. Ask the mentor for a hint only when you want one.

The SRE reviewer assesses your submitted reasoning and evidence, challenges unsupported conclusions and weak comparisons, and records process quality independently of whether your correction works. The reviewer does not automatically execute the investigation or disclose causes. Repository capability gaps are recorded as coverage limits rather than filled with artificial failures.

## Locations

- `source/debezium/`: shallow detached checkout, exact SHA in `pins.json`.
- `fixtures/MySqlKeepAliveDataLossIT.java`: original reporter's Apache-licensed integration test.
- `source/debezium/debezium-connector-mysql/target/`: current Maven reports and test artifacts.
- `evidence/`: immutable-by-convention historical command captures. Preserve these before later tests overwrite Maven reports.

The original report and linked issue discussion contain solutions. They are not required for the investigation.
