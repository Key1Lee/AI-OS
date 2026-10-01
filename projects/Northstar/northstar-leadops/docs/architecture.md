# Northstar LeadOps architecture

```text
POST /lead-intake
  -> validate and normalize [deterministic]
  -> atomic Postgres event claim [deterministic]
      -> duplicate/already-processing response
  -> HubSpot search by normalized email [deterministic entity dedupe]
  -> optional non-blocking enrichment boundary
  -> structured language extraction [AI, advisory]
  -> schema validation and scoring [deterministic]
  -> HubSpot create/update [deterministic side effect]
  -> HOT/WARM/COLD/MANUAL_REVIEW [deterministic]
  -> Slack internal notification [deterministic]
  -> Postgres completion audit
  -> HTTP response

Workflow failure
  -> Error Trigger
  -> sanitize and classify
  -> workflow_errors
  -> Slack operations alert
```

## Ownership boundaries

- HubSpot is the customer system of record.
- PostgreSQL owns event state, idempotency, and operational audit data.
- The LLM only converts untrusted prose into a constrained object.
- Code and IF nodes own validation, scores, tiers, writes, retries, and permissions.
- Humans own low-confidence and contractual/security exceptions.

## Duplicate protection

Event idempotency uses the single canonical primary key `source:event_id` and an atomic upsert. No redundant unique constraint competes with that conflict target. It prevents a retried webhook from replaying side effects. CRM entity deduplication separately searches HubSpot by normalized email, allowing a legitimate new event to update an existing contact.

## Recovery

Transient reads and idempotent updates use bounded retries. Authentication failures are recorded and are not automatically reclaimable. Contact creation is attempted once; any error or timeout is followed by a HubSpot search by normalized email. A found contact resumes the workflow, while an unverified outcome becomes `failed` and requires review.

Recent `processing` events are rejected. A stale lock older than 30 minutes or a retryable failed event may be atomically reclaimed, with a maximum of three total attempts. Further replay requires an explicit operator transition using `db/002_operations.sql`.

Slack notifications use `workflow_effects` as a side-effect ledger. Only one execution can claim a notification. If the send outcome is ambiguous, it is marked `unknown` and automatic resend is suppressed to prevent duplicate alerts. Enrichment is currently an intentionally disabled optional boundary (`skipped_optional`), not a live API call.
