#!/usr/bin/env bash
# Shared AI-OS baseline. Independent projects keep their own dependencies.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
python_bin="${PYTHON_BIN:-python3}"
"$python_bin" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
"$python_bin" -m venv .venv/cloud
.venv/cloud/bin/python -m pip install -r scripts/cloud/requirements.txt
.venv/cloud/bin/python -m pip install -e .
printf '\nShared environment ready. Run: bash scripts/cloud/check.sh\n'
