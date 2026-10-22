# Mock assumptions and decision log · 2026-10-20

All business rules here are proposed demonstration requirements. No employer,
HR owner, regulator or benefits provider has approved them. Samsara is a
hypothetical reference only; the fixtures describe Fictional Acme.

1. The enterprise demo uses a separate SQLite file and deterministic lexical
   retrieval. It runs with no network model, Docker, Slack or Workday account.
2. The documented fixture business date is 2026-10-20, configurable through
   `HR_AS_OF_DATE`. Record freshness is evaluated against that date and displayed
   explicitly. These are never represented as live employee balances.
3. Portal bearer credentials and enterprise employee mappings are server-owned.
   Slack signatures prove transport authenticity; a separately bound enterprise
   bearer session proves the employee identity in this mock. A real Slack/SSO
   account-linking and revocation process is an unresolved integration decision.
4. Self PTO access requires `pto:read:self`. HR role alone gives no extra record
   access. A synthetic delegated grant names an exact permitted employee and
   the `pto:read:delegated` permission; production purpose/approval rules remain open.
5. The master inventory is an administrator-owned allowlist of metadata and
   SHA-256 content digests. Source documents cannot approve or reclassify themselves.
   Approval workflow, retention, legal applicability and country policy decisions
   require actual business owners before any production use.
6. General policy excerpts may be shown only when current and applicable. Numeric
   PTO comes only from the mock record source. Eligibility, medical details,
   compensation and plan coverage are escalated; no entitlement is inferred.
7. Proposed release thresholds describe this bounded fixture corpus. Local mock
   latency is not a production availability or latency SLA. No zero-failure result
   proves universal security or semantic understanding.
8. The earlier PostgreSQL/n8n/Qwen policy service stays available through its
   existing entrypoint. This new enterprise entrypoint extends the same package
   with an offline reference runtime; it does not replace learner exercises.
9. Only read operations are implemented. Slack replies are returned over HTTP
   to a simulator; no message is sent to a real person. Read retries are bounded;
   unknown or non-idempotent writes cannot be requested by a model.
10. Cloud deployment, production Terraform and live enterprise specifications
    would add unsupported assumptions. CI validates a release candidate; there
    is no automatic production deployment.

Open business decisions: real SSO and Slack account binding, permitted HR scopes,
policy ownership and conflicts, regional counsel approval, PTO units and accrual
rules, retention/deletion policy, workload, availability, latency, incident owners,
and production release authorization. Each remains proposed rather than invented.
