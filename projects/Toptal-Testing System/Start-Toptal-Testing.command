#!/bin/zsh

set -u

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || {
  echo "Could not open the Toptal-Testing project directory."
  read -r "?Press Return to close."
  exit 1
}

PYTHON_BIN="${TOPTAL_TESTING_PYTHON:-$(command -v python3)}"
if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3 was not found. Install Python 3.11 or newer, then try again."
  read -r "?Press Return to close."
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Python 3.11 or newer is required. Found: $($PYTHON_BIN --version 2>&1)"
  read -r "?Press Return to close."
  exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating the local Python environment…"
  "$PYTHON_BIN" -m venv "$VENV_DIR" || {
    echo "Could not create $VENV_DIR"
    read -r "?Press Return to close."
    exit 1
  }
fi

REQUIREMENTS_HASH="$(/usr/bin/shasum -a 256 "$SCRIPT_DIR/requirements.txt" | /usr/bin/awk '{print $1}')"
INSTALLED_HASH=""
[[ -f "$VENV_DIR/.requirements.sha256" ]] && INSTALLED_HASH="$(<"$VENV_DIR/.requirements.sha256")"
if [[ "$REQUIREMENTS_HASH" != "$INSTALLED_HASH" ]]; then
  echo "Installing application dependencies…"
  "$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt" || {
    echo "Dependency installation failed. Check the network connection and the output above."
    read -r "?Press Return to close."
    exit 1
  }
  print -r -- "$REQUIREMENTS_HASH" > "$VENV_DIR/.requirements.sha256"
fi

PORT="${TOPTAL_TESTING_PORT:-8000}"
URL="http://127.0.0.1:$PORT"

if /usr/bin/curl --silent --fail "$URL/api/health" | /usr/bin/grep -q '"service":"toptal-testing"'; then
  echo "Toptal-Testing is already running at $URL"
  [[ "${TOPTAL_TESTING_NO_BROWSER:-0}" == "1" ]] || /usr/bin/open "$URL"
  exit 0
fi

# Provider credentials and paid-call permissions belong to the shared AI-OS
# environment. The app can start without them and report unavailability safely.
echo "Provider readiness is managed by AI-OS (python -m py_dev ai providers)."

echo "Starting Toptal-Testing at $URL"
"$VENV_DIR/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" &
SERVER_PID=$!

ready=0
for _ in {1..80}; do
  if /usr/bin/curl --silent --fail "$URL/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

if [[ "$ready" -ne 1 ]]; then
  echo "The local server did not become healthy. Review the startup error above."
  wait "$SERVER_PID" 2>/dev/null
  read -r "?Press Return to close."
  exit 1
fi

[[ "${TOPTAL_TESTING_NO_BROWSER:-0}" == "1" ]] || /usr/bin/open "$URL"
echo "Browser opened. Keep this window open while using the assessment."
echo "Press Control-C to stop the local server."
wait "$SERVER_PID"
