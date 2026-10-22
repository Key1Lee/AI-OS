#!/bin/sh
# Start alongside the existing PeopleOps stack; preserve its volumes and workflows.
set -eu
cd "$(dirname "$0")"
docker inspect peopleops-policy-n8n-1 >/dev/null
mkdir -p data
docker compose up -d --wait
for workflow in qualtrics-error-handler.json qualtrics-failure-probe.json qualtrics-to-gold.json samsara-5000.json; do
  docker cp "$workflow" "peopleops-policy-n8n-1:/tmp/$workflow"
  docker exec peopleops-policy-n8n-1 n8n import:workflow --input="/tmp/$workflow"
done
docker exec peopleops-policy-n8n-1 n8n publish:workflow --id=qualtricsGold01
docker exec peopleops-policy-n8n-1 n8n publish:workflow --id=qualtricsGoldError01
docker exec peopleops-policy-n8n-1 n8n publish:workflow --id=qualtricsGoldFailure01
docker exec peopleops-policy-n8n-1 n8n publish:workflow --id=samsaraSurvey5000
docker restart peopleops-policy-n8n-1
printf '%s\n' 'Open http://127.0.0.1:5680/workflow/qualtricsGold01 after n8n finishes starting.'
