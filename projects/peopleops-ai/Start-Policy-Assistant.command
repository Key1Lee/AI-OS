#!/bin/zsh
set -e
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "${0:A:h}/policy_assistant"
uv sync --frozen
if [[ ! -f .env ]]; then
  uv run python scripts/configure.py
fi
uv run python scripts/start_local_qwen.py
docker compose up --build -d --wait
uv run python scripts/ingest.py
open http://127.0.0.1:8810/
