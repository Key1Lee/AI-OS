# Working policy assistant

This directory is a complete, fictional local app authorized on 2026-10-19.
It is separate from learner-owned exercises in `../training/`; do not change
those exercises or infer learner mastery from assistant-written code.

## Enterprise reference mode · 2026-10-20

The latest user master prompt authorizes `app.main`, the SQLite enterprise mock,
requirements, ingestion, evaluations, and CI. Run `make verify` without Docker or
paid keys; default tests use temporary SQLite files. Tests need requirement
markers and BRD requirements need executable evidence. Release evidence must
match the current source fingerprint.

The additive engineering lab uses actual measured stages, executable YAML rules,
SQLite-backed identities/PTO and demo-only failure injection. Test subprocesses
require `lab:run`, fixed suite names and isolated report/coverage directories.
Never add arbitrary commands or paths to HTTP inputs, expose raw process logs,
or let dashboard jobs overwrite canonical verification artifacts. Run the browser
request, failure, identity-switch and actual test-button paths after UI changes.

This orchestrator may read synthetic PTO after explicit self/delegated permission
checks and a server-owned target scope and purpose. No other personal-record tool
or write operation is authorized. Separate Slack HMAC from enterprise identity;
never log employee identifiers, source payloads, questions, or credentials.

The older `app.api` remains the pgvector/Qwen/n8n policy-only entrypoint. Its
regressions are selected explicitly with `pytest --no-cov
tests/test_vertical_slice.py tests/test_policies.py tests/test_providers_and_grounding.py`.
The remaining guidance below describes that preserved mode.

- Read README.md and the relevant source before changing behavior.
- Keep tenant, region, and role checks in SQL before ranking. Never move them
  into the model prompt or apply them after a global top-k query.
- Select the current policy version before ACL checks. Never revive an old
  version because a current version is expired, withdrawn, or restricted.
- Keep answers extractive and citations validated. Personal HR facts require
  a human handoff; this app has no employee-record tools or ticket writer.
- Keep all fixtures fictional and ports bound to loopback. No external provider
  calls without explicit configured opt-in; tests must use mock providers.
- Preserve immutable version content and atomic, idempotent ingestion.
- Run `docker compose --profile test up -d test-db --wait`, then `uv run pytest`.
  Tests truncate only the dedicated `_test` database. Do not run tests against
  the demo or training databases, or concurrently against the shared test DB.
- For workflow changes, run the actual Compose stack and `uv run python
  scripts/smoke.py`; a JSON structure test alone does not verify n8n execution.
- For UI changes, verify the chat and citation behavior in the browser.
- Update docs/verification.md with actual commands/results and any limits.
