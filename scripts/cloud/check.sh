#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
python_bin="$repo_root/.venv/cloud/bin/python"
if [[ ! -x "$python_bin" ]]; then
  printf 'Run bash scripts/cloud/setup.sh first.\n' >&2
  exit 2
fi
"$python_bin" -m unittest discover -s tests -q
"$python_bin" scripts/sync_skills.py --check
"$python_bin" systems-registry/scripts/validate_registry.py
