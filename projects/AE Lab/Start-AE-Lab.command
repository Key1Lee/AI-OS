#!/bin/zsh
# Finder opens .command files in Terminal. Resolve Desktop symlinks to this project.
LAB_DIR="${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cd "$LAB_DIR" || exit 1

if [[ ! -x "$LAB_DIR/.venv/bin/python" ]]; then
  print 'The Lab environment is missing. In this project, run: uv sync --extra dev'
  result=1
else
  print 'Analytics Engineering Lab — browser practice'
  print 'Opening the local Lab in your browser. Keep this window open while learning.'
  print ''
  # Reuse only this Lab's server when the shortcut is opened twice.
  if [[ $# -eq 0 ]] && "$LAB_DIR/.venv/bin/python" -c 'import json, urllib.request; from pathlib import Path; r=json.load(urllib.request.urlopen("http://127.0.0.1:8088/api/health",timeout=1)); assert r.get("app")=="ae-lab-browser-v1" and Path(r["state_dir"]).resolve()==Path(".lab").resolve()' 2>/dev/null; then
    open 'http://127.0.0.1:8088'
    result=$?
  else
    "$LAB_DIR/.venv/bin/python" -m lab.web "$@" --open
    result=$?
  fi
fi

if [[ -t 0 ]]; then
  print ''
  read '?Press Return to close this session.'
fi
exit "$result"
