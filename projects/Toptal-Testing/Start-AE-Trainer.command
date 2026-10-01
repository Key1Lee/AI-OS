#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import duckdb, sqlalchemy, alembic, yaml, fastapi' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements-ae.txt
fi
if [[ ! -f apps/web/dist/index.html ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    print "Node.js 22.12+ and npm are needed for the initial UI build. Run make setup after installing Node."
    exit 1
  fi
  npm --prefix apps/web ci --no-audit --no-fund
  npm --prefix apps/web run build
fi

if curl -fsS http://127.0.0.1:8001/api/health >/dev/null 2>&1; then
  if curl -fsS http://127.0.0.1:8001/api/health | .venv/bin/python -c 'import sys,json; sys.exit(json.load(sys.stdin).get("service") != "senior-ae-trainer")'; then
    open http://127.0.0.1:8001
    exit 0
  fi
  print "Port 8001 is used by another service. Stop that service before launching."
  exit 1
fi

.venv/bin/python -m uvicorn apps.api.main:create_app --factory --host 127.0.0.1 --port 8001 &
ae_server_pid=$!
trap 'kill "$ae_server_pid" 2>/dev/null || true' EXIT INT TERM
for ae_tick in {1..50}; do
  if curl -fsS http://127.0.0.1:8001/api/health >/dev/null 2>&1; then
    open http://127.0.0.1:8001
    print "Senior AE Trainer is running. Keep this terminal open. Press Control-C to stop."
    wait "$ae_server_pid"
    exit 0
  fi
  if ! kill -0 "$ae_server_pid" 2>/dev/null; then
    wait "$ae_server_pid"
    exit 1
  fi
  sleep 0.2
done
print "The trainer did not become ready. Inspect the startup error above."
exit 1
