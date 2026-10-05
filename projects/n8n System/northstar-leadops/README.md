# Northstar LeadOps

Production-style n8n portfolio workflow for reliable inbound lead qualification and CRM routing. AI interprets prose; deterministic logic owns validation, scoring, routing, persistence, and side effects.

## Components

- `workflows/northstar-error-handler.json`: sanitized error audit and operations alert.
- `workflows/northstar-leadops.json`: authenticated intake, atomic claim, HubSpot dedupe/upsert, structured AI extraction, scoring, routing, Slack, audit, and response.
- `db/001_schema.sql`: PostgreSQL event and error tables.
- `fixtures/*.json`: 15 synthetic scenarios with expected outcomes.
- `scripts/validate.mjs`: offline structural, security, scoring, and fixture checks.

## Setup

1. Apply `db/001_schema.sql` to PostgreSQL/Supabase.
2. Import the error workflow first, then the main workflow.
3. Create n8n credentials for PostgreSQL, HubSpot OAuth2, OpenAI, Slack, and Webhook Header Auth. Assign them to the matching nodes.
4. Confirm Slack channels `#sales-hot-leads`, `#revops-review`, and `#revops-ops` exist.
5. In HubSpot create the custom properties referenced by the HTTP request bodies, or map them to existing properties.
6. Open the main workflow, verify the error workflow setting resolves to `Northstar LeadOps - Error Handler`, test, then publish.

No secrets belong in workflow JSON or Git. `.env.example` is a credential inventory only; n8n credentials remain encrypted in n8n.

## Import and validate

```powershell
node .\northstar-leadops\scripts\validate.mjs
node .\northstar-leadops\scripts\test-behavior.mjs
docker compose exec -T n8n n8n import:workflow --input=/workflows/northstar-error-handler.json
docker compose exec -T n8n n8n import:workflow --input=/workflows/northstar-leadops.json
```

With this repository's existing read-only workflow mount, first copy the two files into `n8n/workflows/`, then use `/workflows/northstar-error-handler.json` and `/workflows/northstar-leadops.json` in the commands. Alternatively, import both JSON files through the n8n UI.

## Test request

After publishing, send the `input` object from `fixtures/01_hot_lead.json` to the production webhook with the configured secret header:

```powershell
$fixture = Get-Content -Raw .\northstar-leadops\fixtures\01_hot_lead.json | ConvertFrom-Json
$body = $fixture.input | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5678/webhook/lead-intake -Headers @{ 'X-Northstar-Secret' = '<secret>' } -ContentType 'application/json' -Body $body
```

Run duplicate testing by submitting the same `event_id` twice. Use fixture `09` or `14` to demonstrate manual review. External-failure fixtures describe mock sequences for a controlled staging environment; do not induce failures against production accounts.

## Failure behavior

- Invalid input returns 422 before AI, CRM, or event claim.
- Completed duplicates return HTTP 200 `duplicate_ignored`; recent processing returns HTTP 200 `already_processing`; non-reclaimable failures return HTTP 409 `failed_requires_operator`, all without repeated side effects.
- LLM errors retry once, then produce invalid/low-confidence advisory data and manual review.
- HubSpot search and idempotent update retries are bounded. Contact creation is never blindly retried; an error triggers an email search to verify whether the create occurred.
- HubSpot 401 is recorded as a non-retryable configuration failure. Automatic event reclaim is limited to retryable failures and at most three attempts.
- Manual-review leads receive no automated customer communication.
- Slack sends are guarded by a unique effect claim. An ambiguous send becomes `unknown` and is not automatically resent.
- Stale `processing` events can be reclaimed after 30 minutes. Controlled operator replay uses `db/002_operations.sql`.
- Optional enrichment is currently disabled and reported as `skipped_optional`.

## Deterministic versus AI

AI may return only `intent`, `pain_points`, budget/urgency bands, recommended next action, confidence, and summary. Its output is schema-checked. AI never chooses a numeric score, tier, write, retry, permission, or customer commitment.

## Portfolio demo (3-5 minutes)

1. Submit fixture `01`; show atomic claim, structured AI result, deterministic score, HubSpot write, HOT Slack alert, and completed audit.
2. Submit it again; show `duplicate_ignored` and no repeated CRM/Slack side effects.
3. Submit fixture `09` or `14`; show MANUAL_REVIEW, preserved CRM data, RevOps alert, and no customer-facing action.
4. Show the error workflow and explain why an unknown CRM timeout outcome is verified before replay.
