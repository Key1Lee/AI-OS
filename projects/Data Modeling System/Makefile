.PHONY: setup build test test-web check run dev-api dev-web contracts

setup:
	uv sync --extra dev
	npm --prefix apps/web ci
	npm --prefix apps/web exec -- playwright install chromium

build:
	npm --prefix apps/web run build

test:
	uv run pytest

test-web: build
	npm --prefix apps/web run test:e2e

check: test test-web

run: build
	uv run python scripts/run.py

dev-api:
	uv run python scripts/run.py --api-only

dev-web:
	npm --prefix apps/web run dev

contracts:
	uv run python scripts/export_contracts.py
