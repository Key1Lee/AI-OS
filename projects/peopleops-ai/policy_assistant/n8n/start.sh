#!/bin/sh
set -eu
n8n import:workflow --input=/workflows/peopleops-policy.json
n8n publish:workflow --id=peopleopsPolicy01
exec n8n start
