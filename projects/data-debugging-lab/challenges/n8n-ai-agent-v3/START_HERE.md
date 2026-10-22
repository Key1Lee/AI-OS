# Enterprise request reliability: n8n AI Agent V3

This is a second, independent track in the existing data-debugging-lab. You will investigate real, unpatched n8n code using two synthetic employee requests. No paid model, real employee data, HR account, or Qualtrics account is needed.

## Start now

Docker Desktop must be running. The checkout, dependencies, and compiled prerequisites are already prepared on this computer.

```bash
cd /Users/key/_AI-OS/projects/data-debugging-lab/challenges/n8n-ai-agent-v3
./scripts/lab versions
./scripts/lab unit
./scripts/lab run pair
```

The last command currently exits **1** because a business assertion fails. Keep its evidence; do not repair anything yet. It starts an ephemeral container and a loopback mock API, executes the real node, writes artifacts, and stops. There is no persistent web server to open and no cleanup required after a run.

To reconstruct dependency/build artifacts:

```bash
./scripts/lab setup
```

Setup downloads public dependencies with the existing frozen lockfile. Tests run without external networking. See [BASELINE.md](BASELINE.md) for actual execution and disclosed setup adjustments.

## System under investigation

Repository: `source/n8n`, pinned to `50c3d88af56ebb869f76f13a2417c528d90ffd4c`. The existing source files and tests are unmodified. Agent node version **3** is distinct from the repository/package release **2.31.0**.

```text
Synthetic request items (independent IDs)
    -> original n8n Agent V3 public execute entry
    <-> original LangChain tool-calling sequence <-> deterministic local model
    <-> engine request/response adapter -> loopback HR / survey mock API
    -> node output, execution history, receipts, and reconciliation artifacts
```

The external harness supplies the execution context and schedules requested tool actions. n8n's actual batching, agent orchestration, tool-call construction, and intermediate history run unchanged. The full n8n workflow engine, UI, database, scheduler, and persistent credentials are outside this package-level baseline. The harness reuses the upstream Vitest configuration and its DI test stubs. Read [RUNBOOK.md](RUNBOOK.md) before expanding the runtime boundary.

## First challenge: prove the employee-service contract

Employee A (`REQ-HR-001`) requests one payroll correction **service record**. Employee B (`REQ-SURVEY-002`) requests one **draft** survey. Neither request authorizes a payment, publication, invitation, or access to the other employee's data.

Write the expected contract before opening implementation code. Run the pair and reconcile the two input identities against outputs, tool activity, and external receipts. Determine which claims you can support and which remain unknown. A completed response alone does not establish safe fulfillment.

Follow the user-supplied sequence: **Business Contract → Observe → Reconcile → Localize → Hypothesize → Experiment → Reproduce → Validate**. Begin a copy of [INVESTIGATION_LOG.md](INVESTIGATION_LOG.md). Your first deliverable is an evidence-backed account of business correctness, with observations separated from hypotheses; a fix is not required at this stage.

Success ultimately requires two correct completions, one authorized intended effect per request, consistent receipts, complete request-specific history, zero cross-request context or actions, and zero unintended duplicate effects. See [EVALUATION.md](EVALUATION.md) for separate process and correction gates, and [CHALLENGES.md](CHALLENGES.md) for later stages. Hints and solutions are supplied only when explicitly requested.
