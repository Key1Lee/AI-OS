.PHONY: setup test check demo learn

setup:
	uv sync --extra dev

test check:
	uv run pytest -q

demo:
	uv run lab --state-dir .lab/demo demo

learn:
	uv run lab learn ORCH-IDEMPOTENCY-001
