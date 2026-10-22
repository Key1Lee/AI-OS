# Samsara People Analytics — synthetic local demo

This application is authorized implementation work, separate from the PeopleOps
interview curriculum. Keep all changes inside this directory. No real employees,
Samsara results, credentials, accounts or live Qualtrics connections are allowed.
Bind exposed Docker ports to loopback. Preserve the other PeopleOps applications.

## Four lightweight logical roles

- **Survey Request Agent**: `web/src/lib/assistant.ts`; uses the existing local Qwen model to convert natural
  language into allowlisted year, department and metric plans. Reject unknown
  topics, arbitrary SQL, URLs and individual answers. Model proposals are validated against local allowlists. `request.ts` retains
  strict filter validation and historical deterministic examples.
- **Analytics Agent**: `web/src/lib/metrics.ts`; deterministically deduplicates,
  validates and calculates respondent-weighted company, department and pooled
  metrics. Never use generative reasoning for calculations.
- **RAG Knowledge Agent**: `web/src/lib/rag.ts`; ranks only the four approved local
  Markdown documents and returns document names and supporting excerpts. Documents
  explain methodology; they never supply measured survey scores.
- **Verification Agent**: `web/src/lib/verification.ts`; checks every report field
  and the source checksum against the independently generated Python reference.
  PASS requires completed comparisons. FAIL or unavailable reference withholds
  numerical reports; unavailable validation is NOT VERIFIED.

These roles are modules. The existing Mac Qwen runtime powers question interpretation
and extractive evidence selection through `qwen.ts`. Never use an LLM for arithmetic
or display model-generated numbers. Validate selected fact/passage IDs and render
only approved evidence. No cloud fallback or provider URL supplied by a question.
`/api/chat` must execute n8n, with timeouts and no hidden local fallback. n8n may
call the interpretation, mock, metrics, RAG and grounded-answer APIs; those APIs must never call n8n.

## Checks

From this directory:

```sh
python3 scripts/verify.py
python3 -m unittest discover -s tests -p '*_test.py' -v
npm --prefix web test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
docker compose up --build -d
python3 scripts/integration.py
python3 scripts/qwen_integration.py
```

After workflow changes, regenerate with `npm --prefix web run workflow`,
then restart n8n. The startup script imports changed workflow JSON before starting
the service. Do not use the Python calculator as a wrapper for TypeScript or
silently rewrite the golden reference to hide a discrepancy. Seed/reference
regeneration is explicit: `python3 scripts/seed_data.py`, then
`python3 scripts/verify.py --write`. Rebuild the web image afterward.
