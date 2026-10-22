#!/bin/zsh
set -e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "${0:A:h}/policy_assistant"
uv sync --frozen
uv run python -m ingestion.run_pipeline
open http://127.0.0.1:8811/
uv run uvicorn app.main:app --host 127.0.0.1 --port 8811 --no-access-log
