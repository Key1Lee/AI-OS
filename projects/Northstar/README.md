# Northstar LeadOps workspace

This repository contains an n8n lead-intake workflow and a local n8n runtime.
The implemented business process lives in [`northstar-leadops/`](northstar-leadops/);
the root `compose.yaml` and `n8n/` directory provide the local runner and
tracked workflow exports. The nested workflow exports and the copies mounted
under `n8n/workflows/` are currently identical.

Start with the [business process](northstar-leadops/docs/process.md), then the
[implementation map](northstar-leadops/docs/architecture.md). The
[integration inventory](northstar-leadops/docs/integrations.md) records the
external systems and the remaining setup choices. Boundary schemas are in
`northstar-leadops/contracts/`.

Run the existing offline checks from the repository root:

```bash
node northstar-leadops/scripts/validate.mjs
node northstar-leadops/scripts/test-behavior.mjs
```

These checks execute local code and inspect workflow exports and synthetic
fixtures. They do not prove that n8n, PostgreSQL, HubSpot, OpenAI, or Slack is
connected or that a full business outcome occurred. Import and stage-test the
workflow only with test credentials and synthetic leads; see the
[implementation README](northstar-leadops/README.md) for setup.

`AGENTS.md` contains the durable working rules for this repository.
