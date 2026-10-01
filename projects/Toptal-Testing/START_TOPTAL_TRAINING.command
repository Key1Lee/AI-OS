#!/bin/zsh
set -u

PROJECT_DIR="${0:A:h}"
VENV_DIR="$PROJECT_DIR/.venv"
STAMP_FILE="$VENV_DIR/.training-requirements.sha256"

cd "$PROJECT_DIR" || exit 1

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating local Python environment..."
  python3 -m venv "$VENV_DIR" || {
    echo "Could not create .venv. Install Python 3 and try again."
    read -r "?Press Enter to close. "
    exit 1
  }
fi

REQUIREMENTS_HASH="$(shasum -a 256 requirements.txt | awk '{print $1}')"
INSTALLED_HASH=""
if [[ -f "$STAMP_FILE" ]]; then
  INSTALLED_HASH="$(<"$STAMP_FILE")"
fi

if [[ "$REQUIREMENTS_HASH" != "$INSTALLED_HASH" ]]; then
  echo "Installing project dependencies..."
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt || {
    echo "Dependency installation failed. Check the output above."
    read -r "?Press Enter to close. "
    exit 1
  }
  print -r -- "$REQUIREMENTS_HASH" > "$STAMP_FILE"
fi

"$VENV_DIR/bin/python" -m training.cli
STATUS=$?

if [[ -t 0 ]]; then
  echo
  read -r "?Press Enter to close. "
fi
exit "$STATUS"
