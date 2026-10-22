# PeopleOps AI — working policy assistant

> **New enterprise reference:** [Setup, requirements, source tracing, tests and evaluations](docs/enterprise-guide.md).
> **Interactive engineering layer:** [Dashboard, failure controls and real backend test runs](docs/testing-layer-guide.md).
> Run `make verify` for the standalone SQLite mock and `make run` for its portal
> on port 8811. It implements signed Slack requests, exact authorized synthetic
> PTO, governed RAG, redacted audit, 105 labeled evaluation cases, and CI gates.
> The guide below describes the earlier PostgreSQL/n8n/Qwen policy service on 8810.

A complete local vertical slice for a **fictional** company: Markdown policies →
authenticated FastAPI → permission-filtered pgvector retrieval → checked source
excerpts → n8n → chat. It never reads employee records or invents personal balances,
eligibility, pay, or benefit coverage. A private HR handoff is guidance only; no
ticket or external message is sent.

This app is separate from `../training/`, whose exercises remain learner-owned.
The earlier project foundation was the available starter; no additional archive
was visible with the implementation request.

> This Mac is now configured to use its installed **local Qwen3-4B-Q4_K_M** for
> the policy LLM and the n8n Assistant model connection. See
> [local Qwen setup and startup](docs/local-qwen.md). Fresh generated configs still
> default to offline mocks; the embedding provider remains the mock in both modes.

## Start on this computer

Prerequisites: running Docker Desktop with Compose, and `uv`. uv selects Python
3.12 from `.python-version`. No paid API key or n8n account is needed for this demo.

```sh
cd /Users/key/_AI-OS/projects/peopleops-ai/policy_assistant
uv sync --frozen
# First run only: creates random credentials; refuses to overwrite existing files.
uv run python scripts/configure.py
# Needed when this existing .env selects qwen_local; otherwise this is a no-op.
uv run python scripts/start_local_qwen.py
docker compose up --build -d --wait
uv run python scripts/ingest.py
uv run python scripts/smoke.py
```

Open <http://127.0.0.1:8810/>. Paste the `employee-us` token from the generated
`access-tokens.json` into the connection field. `employee-gb`, `hr-us`, and `admin`
are also available for local access tests. Tokens are held in browser memory,
cleared on reload/disconnect, and never saved in browser storage. `.env` stores
only SHA-256 token hashes and server-side identities; both local secret files
are ignored by Git and have owner-only permissions.

On later runs, double-click **`../Start-Policy-Assistant.command`**, or run the
Compose and ingestion commands above. Re-ingestion preserves policy versions.
The launcher preserves existing credentials. It does not install Docker or uv.

All published ports bind to loopback:

| Service | Address | Purpose |
| --- | --- | --- |
| FastAPI and chat | `127.0.0.1:8810` | `/ask`, `/chat`, static UI |
| PostgreSQL/pgvector | `127.0.0.1:55433` | Dedicated `peopleops_policy` database |
| n8n | `127.0.0.1:5680` | Imported and published policy webhook |
| Test database | `127.0.0.1:55434` | Disposable `peopleops_policy_test`, test profile |

The n8n workflow is usable without opening its editor or completing an owner
account setup. If you choose to use the editor, complete its local setup yourself.

## Example requests

These commands load a local token without printing it:

```sh
uv run python scripts/example_requests.py "How do I request PTO?"
uv run python scripts/example_requests.py "How does benefits enrollment work?" --via chat
uv run python scripts/example_requests.py "What is the parental leave process?" --via webhook
uv run python scripts/example_requests.py "What is the remote work policy?" --identity employee-gb
uv run python scripts/example_requests.py "Employee needs help with payroll" --via chat
uv run python scripts/example_requests.py "What is my PTO balance?"
uv run python scripts/example_requests.py "What is the sabbatical policy?"
```

For curl, read a token without putting the literal secret in command history:

```sh
read -r -s PEOPLEOPS_TOKEN
curl -sS http://127.0.0.1:8810/ask \
  -H "Authorization: Bearer $PEOPLEOPS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"question":"How do I request PTO?"}'
unset PEOPLEOPS_TOKEN
```

An answered response has this shape (IDs abbreviated here):

```json
{
  "status": "answered",
  "answer": "Relevant fictional policy excerpts (not a personal entitlement decision):\n\n[1] Submit PTO requests through the authenticated HR portal. Your manager reviews the request before leave is scheduled. Submit planned PTO at least five business days ahead where possible.",
  "citations": [{
    "policy_id": "pto", "version": 2, "title": "Paid time off",
    "section": "PTO / Requests", "chunk_id": "...", "source": "pto-v2.md",
    "effective_on": "2025-01-01",
    "quote": "Submit PTO requests through the authenticated HR portal. Your manager reviews the request before leave is scheduled. Submit planned PTO at least five business days ahead where possible."
  }],
  "escalation": null,
  "request_id": "...",
  "mode": "LLM: mock · embeddings: mock"
}
```

Statuses are `answered`, `abstained`, `escalated`, `refused`, and `unavailable`.
Each uses the same response schema. Business outcomes use HTTP 200; invalid
authentication is 401, missing admin permission 403, version conflicts 409,
invalid inputs 422, oversized requests 413, and database/workflow outages 503.
An invalid LLM selection returns `unavailable` without a fabricated answer.

## Policies and ingestion

Eight supplied Markdown files contain seven policy IDs and nine chunks,
including old/new PTO, benefits, parental leave, US/GB remote work, payroll
support, and an HR-only procedure. Dates and rules are fictional.

```yaml
---
policy_id: example-policy
version: 1
title: Example policy
effective_on: 2025-01-01
regions: [US, GB]
roles: [employee, manager, hr, admin]
---
# Example
## Procedure
An approved, fictional policy paragraph goes here.
```

Optional metadata: `expires_on` (exclusive end date) and `withdrawn: true`.
Use `regions: ['*']` for all regions. Roles are explicit: an admin has no implicit
retrieval bypass. The tenant comes from the authenticated admin, never Markdown.

`POST /admin/ingest` accepts
`{"documents":[{"filename":"example.md","markdown":"---\n..."}]}`.
Only admin tokens may call it. `scripts/ingest.py` submits all files in `policies/`.
Limits are 20 documents per batch, 100,000 characters per document, 150 chunks
per document, and 512,000 actual bytes per HTTP request. Send larger corpora in
smaller batches. Headings become section paths; long sections split into exact
excerpts of at most 1,200 characters. Code fences and common instruction attacks
are rejected for manual policy review.

The key is `(tenant, policy_id, integer version)`. Identical normalized content
returns `unchanged` without another embedding call. Changed content or metadata
under the same version returns 409 and rolls back the **whole batch**. Publish a
new increasing version to change a policy. A renamed delivery retains the original
source filename. A tenant-scoped transaction lock also handles concurrent retries.

The highest version already effective on the server's date is authoritative.
Expired or withdrawn latest versions do not fall back to an older version.
Future versions do not hide today's version. A newly restricted version cannot
resurrect an old public version. Use separate policy IDs for regional variants,
as shown by `remote-us` and `remote-gb`.

## Retrieval and providers

1. Verify the bearer token against the server's hashed identity map.
2. Escalate personal HR questions before any provider call.
3. Select current policy versions for that tenant.
4. Materialize region/role-authorized chunks **before** cosine ranking and top-k.
5. Give only those chunks to the selector; it returns IDs, not answer text.
6. Validate IDs, then build the final answer from exact excerpts and citations.

`TOP_K` defaults to 5 and `MIN_SIMILARITY` to 0.18. Scores are similarity, not
confidence. Exact pgvector cosine search is deliberate for this small corpus;
there is no approximate vector index that could filter after candidate selection.

Default mode uses a **deterministic word-hash embedding mock** and a strict word
matcher. It is an offline demo, not neural semantic understanding. It may abstain
on paraphrases. The configurable embeddings adapter enables semantic embeddings,
and the chat adapter uses an OpenAI-compatible provider to select evidence.

To enable the provider, edit `.env` deliberately:

```dotenv
LLM_PROVIDER=openai_compatible
EMBEDDING_PROVIDER=openai_compatible
PROVIDER_BASE_URL=https://your-provider.example/v1
PROVIDER_API_KEY=your-provider-key
LLM_MODEL=your-chat-model
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSIONS=256
ALLOW_EXTERNAL_PROVIDER=true
```

Choose an embedding model that accepts the configured `dimensions` parameter.
The chat endpoint must support JSON response format and `max_completion_tokens`.
The two providers can be configured independently. A local compatible server can
omit the API key; for a host service from Docker, use `host.docker.internal` in its
base URL. Provider requests have bounded timeouts and do not follow redirects.

After changing settings:

```sh
docker compose up -d --force-recreate api
uv run python scripts/ingest.py
```

Embeddings are namespaced by provider URL, model, and dimensions; mock spaces also
include a vocabulary fingerprint. Re-ingestion adds the new space without changing
immutable policy content. Queries never mix spaces. Re-ingest all current sources
before using a changed embedding configuration. Adjust the similarity threshold
using representative evaluations for the selected model. This run made no live
external model calls; transport tests use `httpx.MockTransport`.

## n8n

`n8n/peopleops-policy.json` is directly importable. The supplied container imports
and publishes it on startup. The JSON file is the source of truth, so persist
editor changes back to it before restarting. Startup re-imports this one ID;
it does not modify other workflows.

```text
Browser → POST /chat → n8n POST /webhook/peopleops-policy
                              → FastAPI POST /ask
                              ← answer + citations + status
Browser ← validated structured response
```

The HTTP node forwards the caller's Authorization header to a fixed FastAPI URL;
it does not hold an admin token. FastAPI remains the authentication boundary,
including for direct webhook requests. n8n propagates FastAPI's status and JSON.
The workflow makes no HR decisions, calls no tools, and sends no external chat
messages. Successful, failed, and manual execution-data retention are disabled
to avoid storing bearer tokens or questions in n8n history.

To import into another **local** n8n instance, adjust the HTTP node's fixed API
URL to the appropriate private address, then import the JSON. CLI equivalent:

```sh
n8n import:workflow --input=peopleops-policy.json
n8n publish:workflow --id=peopleopsPolicy01
# Restart n8n if the CLI commands were run while it was already running.
```

References used: [n8n CLI import/publish](https://docs.n8n.io/hosting/cli-commands/),
[Respond to Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/),
[OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
and [embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create).

## Tests and operations

```sh
docker compose --profile test up -d test-db --wait
uv run pytest --no-cov tests/test_vertical_slice.py tests/test_policies.py tests/test_providers_and_grounding.py
uv run python scripts/smoke.py
```

These preserved policy tests require real local PostgreSQL/pgvector and use only mock embeddings/LLM
transports. It truncates **only** the dedicated database ending in `_test`, never
the demo database. To run the same tests under container Python 3.12:

```sh
docker compose run --rm \
  -e TEST_DATABASE_URL=postgresql://test:test-local-only@test-db:5432/peopleops_policy_test \
  api python -m pytest --no-cov -o cache_dir=/tmp/pytest-cache \
  tests/test_vertical_slice.py tests/test_policies.py tests/test_providers_and_grounding.py
```

Do not run the host and container database tests simultaneously; they share the
test database. See [actual verification evidence](docs/verification.md) and the
[elementary function tour](docs/functions.md).

Both `GET /health` and `GET /admin/health` require an admin bearer token and check
database readiness without disclosing secrets. Compose probes the static root
page for process liveness; that probe does not prove database or model readiness.
`/me` shows the authenticated identity and active provider modes.

```sh
docker compose ps
docker compose logs --tail 50 api n8n
docker compose --profile test down
```

Stopping preserves policy and n8n named volumes. The test database uses tmpfs.
Do not add `-v` unless you intend to erase this demo's stored policies and n8n
state. Back up PostgreSQL and the n8n volume before deliberate schema changes.
The current schema initializer creates v1 tables; it is not a future migration
engine. Dependency changes require updating `uv.lock` and re-exporting hashed
requirements with `uv export --frozen --no-emit-project --format requirements-txt --output-file requirements.txt`.

## Production-inspired scope

This is a runnable fictional local application, not a production HR deployment.
The preserved boundaries are server-side tenant/region/role authorization,
immutable versions, atomic ingestion, bounded requests, exact citations, no
record tools, and no autonomous employee decisions. Prompt-pattern detection is
an English-focused extra guard, not proof against every prompt injection; even
when it misses, the model cannot change SQL permissions or write arbitrary claims.

Production deployment still needs an organizational identity provider and token
rotation, TLS, rate limits, database least-privilege roles, backups, policy-owner
review, and representative semantic-model evaluation. The supplied DB user is a
local bootstrap user. n8n's local HTTP cookie setting is for loopback only. Auth
tokens identify a demo persona, not a real employee. No real HR integrations or
production deployment were performed.
