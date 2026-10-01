.PHONY: setup dev test lint seed test-e2e check-map-demo

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-ae.txt -r requirements-dev.txt
	npm --prefix apps/web ci --no-audit --no-fund
	npm --prefix apps/web run build

dev:
	.venv/bin/python -m uvicorn apps.api.main:create_app --factory --host 127.0.0.1 --port 8001

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/python -m compileall -q trainer data_system_map apps/api
	npm --prefix apps/web run typecheck
	zsh -n Start-AE-Trainer.command

seed:
	.venv/bin/python scripts/seed_ae.py

test-e2e:
	npm --prefix apps/web run test:e2e

check-map-demo:
	.venv/bin/python scripts/generate_commerce_map.py --check
