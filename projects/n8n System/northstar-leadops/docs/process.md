# Workflow 001 — inbound lead qualification

This is the business behavior extracted from the current Northstar LeadOps
workflow and fixtures. `DETERMINISTIC`, `AI_ASSISTED`, and `HUMAN` describe who
or what makes each decision. The [architecture](architecture.md) maps it to
nodes and storage.

## Purpose

Accept a consented inbound lead once per source event, find or create its CRM
contact, qualify it, route internal attention, and retain an outcome that can
be audited and recovered.

## Trigger

An authenticated HTTP `POST /lead-intake` webhook. Authentication is configured
as n8n Webhook Header Auth; the specific test credential is not in Git.

## Inputs

An event ID, source, lead email, message, and `consent_to_contact: true` are
required by the current validator. Other lead and campaign fields are optional.
Whitespace is trimmed; source and email become lowercase. See the
[input contract](../contracts/lead-intake.schema.json). The validator accepts
extra fields but does not put arbitrary extra fields in the normalized output.

## Preconditions

- The webhook credential is configured in n8n.
- PostgreSQL tables in `db/001_schema.sql` exist and the workflow can use them.
- HubSpot, OpenAI, and Slack test credentials and required CRM properties are
  configured for a live run.
- Consent is provided by the caller. The workflow checks the boolean; it does
  not independently verify how consent was collected.

## States

- `lead_events`: `processing`, `completed`, `failed`.
- `workflow_effects` for Slack: `processing`, `completed`, `unknown`, `failed`.
- HTTP outcome: validation error, duplicate/already processing, operator
  intervention required, accepted, or CRM failure.
- `awaiting_human_review` is a response label for a completed event that needs
  a person to inspect it. It is not a durable `lead_events` state, and the
  workflow does not record a human's final decision.

## Happy Path

1. Validate and normalize the event (`DETERMINISTIC`). Reject bad input before
   database, AI, CRM, or Slack work.
2. Claim `source:event_id` in PostgreSQL (`DETERMINISTIC`).
3. Search HubSpot by normalized email (`DETERMINISTIC`). This checks whether
   the person already exists; it is separate from the event claim.
4. Extract constrained intent, pain points, budget/urgency bands, a suggested
   action, confidence, and summary from the message (`AI_ASSISTED`). Optional
   enrichment is currently skipped.
5. Validate the AI shape and business conflicts, calculate a numeric score,
   and set HOT/WARM/COLD/MANUAL_REVIEW (`DETERMINISTIC`).
6. Update or create the HubSpot contact (`DETERMINISTIC` write). An uncertain
   create outcome is checked by email before any further decision.
7. Claim the internal Slack notification effect and send it when needed
   (`DETERMINISTIC` write). Cold leads have no urgent notification.
8. Mark the event complete in PostgreSQL and return the HTTP outcome.

## Decisions

| Decision | Owner | Current rule |
|---|---|---|
| Is input acceptable? | DETERMINISTIC | Required fields, basic email syntax, message length, employee count, and consent check |
| Is this exact event already claimed? | DETERMINISTIC | Atomic PostgreSQL `source:event_id` claim and bounded reclaim |
| Does this person exist? | DETERMINISTIC | HubSpot email lookup |
| What does the message say? | AI_ASSISTED | Structured extraction only; no permission or side effect |
| Is AI output usable? | DETERMINISTIC | Allowed keys/values and conflict checks; otherwise manual review |
| What score/tier applies? | DETERMINISTIC | Numeric rules in `Validate AI + Score & Route [D]` |
| Should a person review? | DETERMINISTIC → HUMAN | Workflow flags and notifies; human disposition is outside this workflow |

## Business Rules

- A matching `source:event_id` is the same event. A matching normalized email
  is the same CRM person, even for a new event.
- The current score gives 25 points for 50–500 employees, 20 for senior title,
  20 for a budget band of at least 25k, 15 for a timeline within 30 days, 15
  for automation-project intent, and 5 for a non-free email domain. HOT is 75+
  and WARM is 50–74; otherwise COLD unless a review condition applies.
- Invalid/low-confidence AI output, explicit-budget conflict, prompt-injection
  signal, legal/security commitment, or spam/score conflict forces
  MANUAL_REVIEW. AI cannot set the score or tier directly.
- A manual-review flag sends an internal RevOps notice. The workflow does not
  send an automated customer message.

## External Systems

PostgreSQL owns event and effect state; HubSpot owns contacts; OpenAI supplies
advisory extraction; Slack receives internal alerts. See
[integrations.md](integrations.md) for operations and failure boundaries.

## Side Effects

PostgreSQL inserts/updates event and effect rows; HubSpot creates or updates a
contact; Slack may send one internal message. No customer email or financial
transaction is implemented.

## Failure Conditions

- Invalid input (`PERMANENT`): HTTP 422, no event claim or external writes.
- Duplicate/recent processing (`DETERMINISTIC`): HTTP 200 without replaying
  side effects. Non-reclaimable failure returns HTTP 409.
- HubSpot timeout/429/5xx (`TRANSIENT` or `AMBIGUOUS`): bounded read/update
  retry; create is not blindly retried. An unverified create becomes a failed
  event and needs inspection. Authentication failure is non-retryable.
- AI timeout or invalid output (`TRANSIENT` / `PERMANENT`): limited retry,
  then MANUAL_REVIEW using fallback advisory data.
- Slack send uncertainty (`AMBIGUOUS`): effect marked `unknown`; automatic
  resend is suppressed.
- Unhandled workflow error: separate Error Trigger logs a workflow error and
  sends an operations alert when its dependencies work.

## Recovery Paths

The event claim can reclaim a stale processing lock after 30 minutes or an
approved retryable failure, with fewer than three prior attempts. `db/002_operations.sql`
contains operator inspection and explicit replay operations. Unknown Slack
effects require manual verification before marking an outcome. A failed error
audit attempts an alert through the error branch.

## Human Decisions

RevOps/sales must decide the disposition of a MANUAL_REVIEW lead. An operator
must resolve unknown external-write outcomes and approve any replay outside
the automatic claim rule. The current workflow does not implement a formal
approval record or a human-decision callback.

## Outputs

HTTP 422, 200, 409, 503, or 202 with the shapes in the
[response contract](../contracts/lead-response.schema.json). The accepted
response includes an idempotency key, CRM contact ID, score/tier, review flag,
and notification status when available.

## Success Condition

For an accepted, nonduplicate event: one `lead_events` row is completed; one
HubSpot contact exists for the normalized email with the intended properties;
at most one Slack notification effect is claimed for this event; and the
response identifies the CRM contact and route. A green n8n execution alone
does not prove this business result. These postconditions require a controlled
integration test and have not been verified live in this repository.

## Invariants

- Validation precedes all durable or external side effects.
- Only the claim winner can proceed with qualification and writes.
- AI output cannot directly authorize a write, tier, permission, or retry.
- A contact create is never blindly repeated after an ambiguous result.
- An unknown Slack outcome is not automatically resent.
- Local tests use synthetic fixtures and no production integration.

## Out of Scope

Live enrichment, outbound customer communication, human decision recording,
and autonomous agent planning are not implemented. The score thresholds,
target channels, retention period, and approval SLA are present design choices
or open policies, not independently confirmed business requirements.

## Required business confirmations

Before a production launch, confirm who owns the score/tier thresholds, what
constitutes valid consent, what RevOps does with MANUAL_REVIEW and by when, and
which CRM fields may be overwritten. These are business decisions; the current
workflow encodes defaults that should not be mistaken for approved policy.
