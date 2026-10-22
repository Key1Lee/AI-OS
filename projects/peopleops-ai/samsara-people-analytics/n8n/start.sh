#!/bin/sh
set -eu
# Reimport only when the checked-in workflow changes. Keep editor changes otherwise.
signature="$(sha256sum /demo/qualtrics-survey-demo.json | cut -d ' ' -f 1)"
marker="/home/node/.n8n/.samsara-imported"
if [ ! -f "$marker" ] || [ "$(cat "$marker")" != "$signature" ]; then
  n8n import:workflow --input=/demo/qualtrics-survey-demo.json
  n8n publish:workflow --id=samsaraSurveyDemo2026
  printf '%s' "$signature" > "$marker"
fi
exec n8n start
