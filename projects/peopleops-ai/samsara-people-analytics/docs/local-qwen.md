# Local Qwen and grounded survey answers

The app uses the existing AI-OS llama.cpp runtime on the Mac, alias
`Qwen3-4B-Q4_K_M`, served at `127.0.0.1:8080`. Compose connects through
`http://host.docker.internal:8080/v1`. It does not start another model server,
change shared runtime configuration, use a cloud provider or need an API key.

Qwen performs two actual inference calls within the native n8n workflow:

1. Interpret a free-form question as allowlisted intent, years, departments and
   a retrieval query. Canonical filters are validated locally and override scope.
2. Select exact fact and passage IDs from verified aggregates and retrieved local
   Markdown. The app constructs the answer from those approved strings.

Schema-constrained JSON, disabled thinking and temperature zero keep this small
local task bounded. Responses must identify the expected model, finish normally,
contain token usage, and pass local domain validation. No model-generated numbers
or prose are rendered. This is an extractive RAG assistant, using local keyword
retrieval with query rewriting; it is not a vector database or embedding service.
Both calls' actual model, latency and token counts are returned in `ai` receipts.

Questions can cover the available scores, participation, departments, selected
period changes, rankings, valid/eligible counts, cleaning rules, survey question
wording, formula, weighting and limitations. No specified year means all three
years. Latest/current means 2026 YTD; last year means 2025. Unknown departments,
external facts, actual attrition, individual data and requests to fabricate scores
are declined. The data cannot explain causes or establish statistical significance.
This does not promise answers to every possible question or arbitrary computations.

Check `/health` and `/v1/models` on the host. If stopped, start the existing shared
runtime with `python3 -m py_dev serve` from the AI-OS root. If a different model is
loaded, preserve it and correct the project configuration explicitly. An outage
returns a visible error; the prior verified dashboard remains displayed. Only
local runtime hosts are accepted; redirects and question-supplied endpoints are
unavailable. The project owns all prompts, evidence selection and business rules.

Run `python3 scripts/checks.py`, build/start Compose, restart n8n after generated
workflow changes, then run `python3 scripts/integration.py` and
`python3 scripts/qwen_integration.py`. The tests do not stop the shared model or
modify other PeopleOps services. Unit tests inject model failures and malformed
outputs. Live receipts prove actual Qwen calls, n8n execution and Python agreement.
