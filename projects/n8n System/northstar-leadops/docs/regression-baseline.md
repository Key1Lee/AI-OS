# Northstar LeadOps regression baseline

Baseline source: workflow export at commit `2f87c503d78cd5f9636bd8f37e8ed4eeea723840`.
This records the existing repository implementation, not every behavior of a live
HubSpot account. The workflow export is unchanged by this baseline work.

## What is verified offline

Run from the repository root:

```sh
node northstar-leadops/scripts/validate.mjs
node northstar-leadops/scripts/test-behavior.mjs
node northstar-leadops/scripts/regression-baseline.mjs
```

The existing 15 synthetic fixtures encode expected HTTP, CRM, tier, Slack,
human-review, and database outcomes. `test-behavior.mjs` actually executes the
normalization and deterministic scoring Code nodes; `validate.mjs` inspects
workflow structure, constraints, fixture shape, and some safety settings. The
new baseline checks actual normalization and CRM error-classification Code node
outputs, plus static safeguards for HubSpot create and Slack send. None of these
tests executes n8n, PostgreSQL, HubSpot, OpenAI, or Slack.

| Current scenario | Offline observed/checked outcome | Error type |
|---|---|---|
| Valid demo request | Trimmed/lowercase email and source; stable `source:event_id` | none |
| Missing/invalid email, missing consent, missing event ID | Validator marks invalid; export routes invalid branch to HTTP 422 | validation |
| HubSpot 429 or 5xx | CRM failure classifier marks retryable | crm_api |
| HubSpot 400 or 401 | CRM failure classifier marks non-retryable | crm_api |
| HubSpot timeout without status | Classifier marks outcome unknown and retryable; create path requires verification | ambiguous_write |
| Contact creation error | Create node has no blind retry and verification search node exists | ambiguous_write |
| Slack send uncertainty | Effect-claim and unknown-outcome nodes exist; no blind send retry | ambiguous_write |

These are *component/static* observations, not proof of end-to-end side-effect
counts or safe concurrent replay. The fixture expectations for duplicate event,
existing contact, 429 recovery, expired credentials, and final HTTP outcomes
still need controlled integration tests with test accounts and an isolated DB.

## Existing gaps relative to the described business process

- The export validates at the n8n intake boundary before HubSpot, not inside
  HubSpot. Changing that boundary would require an explicit business decision.
- The export does not assign a HubSpot owner, create a follow-up task, or send a
  confirmation to the lead. These are **not regression expectations** yet.
- There is no single record schema for every internal stage: the inbound
  contract, normalized object, AI output, CRM body, and response have different
  shapes by design. Schema compatibility across these boundaries is not fully
  proven by the offline suite.
- HTTP 401, 400, 429, 5xx, and timeout get retryability classification in the
  CRM failure node, but a complete per-operation error policy for *every*
  integration is not yet documented or tested end to end.

## Change gate

Before editing an export, preserve this baseline and identify the intended
behavior change. After each change, rerun all three commands and compare the
same cases. For every failure or changed outcome record: `input`, `expected`,
`actual`, `error_type`, `existed_before_change`, and `caused_by_new_change`.
The baseline runner prints those fields for a failing offline check. For a live
failure, capture the same fields without secrets or real lead data. A new test
failure leaves both regression-causality fields `null` until an engineer compares
it with the recorded baseline; do not guess whether it was pre-existing. Do not call
a change approved merely because the offline suite is green: verify event and
effect rows, HubSpot contact/task counts, notification counts, and response in
an isolated integration run.
