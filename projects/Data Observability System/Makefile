.PHONY: setup dev test lint build check-demo
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e ".[dev]"
	npm --prefix web ci --no-audit --no-fund
	npm --prefix web run build

dev:
	.venv/bin/python -m uvicorn data_system_map.api.main:create_app --factory --host 127.0.0.1 --port 8002

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/python -m compileall -q src
	npm --prefix web run typecheck

build:
	npm --prefix web run build

check-demo:
	.venv/bin/python -m data_system_map.demo.generate --check
