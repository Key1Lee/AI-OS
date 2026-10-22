.PHONY: install ingest run test evaluate check verify
install:
	uv sync --frozen
ingest:
	uv run python -m ingestion.run_pipeline
run:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 8811 --no-access-log
test:
	uv run pytest
evaluate:
	uv run python -m evals.run_evaluations
check:
	uv run python scripts/static_check.py
verify: check test evaluate
