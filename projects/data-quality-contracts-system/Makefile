.PHONY: setup run check contracts check-dbt
setup:
	uv sync --extra dev
	npm --prefix web ci
run:
	uv run python scripts/run.py
check:
	uv run pytest
	npm --prefix web run build
	npm --prefix web run test:e2e
contracts:
	uv run python scripts/export_contracts.py
check-dbt:
	SSL_CERT_FILE="$$(.venv/bin/python -c 'import certifi; print(certifi.where())')" uv run --extra dbt python scripts/check_dbt.py
