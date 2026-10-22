#!/bin/zsh
set -euo pipefail
cd "${0:A:h}/training"
docker compose up --build -d --wait --wait-timeout 120
open http://127.0.0.1:8501
