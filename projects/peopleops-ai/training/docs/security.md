# Security and confirmation contract

The entire deployment is a local synthetic training environment. `/lab/*` and
`/mock/*` deliberately expose fixtures and demo identity switching to the local
developer. They are not protected employee APIs and must never be published or
used with real records. API tokens are random per process, kept only in memory,
and obtained from the local identity simulator. Restart invalidates them.

The business APIs use server-created principals. A role/employee ID supplied in
a question, JSON field, URL, or `X-Role` header never changes the principal.
Authentication plumbing works; record authorization is an unfinished exercise.

## E07 permission matrix

| Action | Allowed |
| --- | --- |
| employee_read | Self or hr_admin; full employee details remain private from managers |
| manager_summary | manager with resource.manager_id == actor employee_id, or hr_admin; summary excludes PTO, benefits, email |
| candidate_read | recruiter or hr_admin |
| analytics_read | analyst or hr_admin |
| jobs_read | Any authenticated role |
| policy_read | audience=all, audience=actor role, or hr_admin |
| pto_create / ticket_create / request_read | Self or hr_admin |
| Unknown action or missing ownership field | Deny |

E08 employee endpoint returns 404 with the same body for out-of-scope and missing
records. Candidate/analytics role denial returns 403 before querying a record.
Responses use minimal fields. No caller can pass arbitrary SQL or a table name.
Recruiter authorization is broad in this lab; assigned-recruiter scoping is a
documented production extension.

## RAG defenses to implement

E05 filters audience, effective date, and retired versions in the database
before ranking and limiting. Fixed evaluation date is 2026-10-01. E06 validates
that returned quotations exist in authorized retrieved sections and retains exact
policy/version/section provenance. Refuse unsupported facts, including personal
compensation and bank details. Clarify vague questions instead of guessing.

Questions and documents are untrusted data. A document saying “ignore the rules”
must not alter the system's tool list, identity, permissions, or confirmation
state. The fake provider has no tool execution capability. Keyword matching is
not a comprehensive injection defense; explain the remaining attack surface.

## E10 write protocol

1. User requests a preview. E09 selects an allowlisted plan with validated input.
2. E10 checks permission and stages a proposal for ten minutes, bound to the actor,
   canonical arguments, and a payload hash. No PTO/ticket business record is created.
3. UI displays the exact proposal. The confirmation checkbox starts unchecked.
4. Confirm endpoint receives proposal ID, explicit confirmation, and idempotency key.
   It accepts no alternate employee, tool, dates, or mutable payload.
5. E10 locks and rechecks ownership, permission, expiry, integrity, and replay state.
   Create request, receipt, and audit row in the caller's transaction.
6. Exact replay returns the original ID with replayed=true. A different proposal
   under the same actor/key, changed hash, or expired unexecuted proposal returns 409.
   Another actor or missing proposal returns 404; confirmed=false returns 400 first.

Preparing a proposal is staging infrastructure; it is not permission to execute
the requested HR action. Only the explicit confirmation route may create those
business records. PTO must have ordered dates, positive hours, and enough balance;
create a pending request without silently approving it or deducting balance.
Support tickets require category and subject. Never include bank details in a ticket.

Unique database constraints support concurrency safety but are not the whole
solution. Demonstrate transaction rollback and reason about two simultaneous
confirmations. External Slack delivery is a later outbox exercise: a local database
transaction cannot guarantee exactly-once execution in an unrelated system.
