#!/bin/zsh
set -eu
cd "${0:A:h}"
if command -v uv >/dev/null 2>&1; then
  uv sync --frozen
  exec uv run peopleops serve
else
  print "Install uv (see README.md), or use the documented Python venv commands."
  read -r "reply?Press Enter to close."
fi
