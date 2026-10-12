# Files created in AE Lab

AE Lab was empty at discovery. All implementation, tests, documents and runtime state are local to this project. No sibling source was edited. Native runtime caches are excluded from this source manifest.

- `.gitignore`
- `Makefile`
- `Start-AE-Lab.command`
- `README.md`
- `docs/adr/001-canonical-event-contract.md`
- `docs/adr/002-adapter-boundary.md`
- `docs/adr/003-local-warehouse.md`
- `docs/adr/004-scenario-state-model.md`
- `docs/adr/005-lineage-integration.md`
- `docs/architecture.md`
- `docs/browser-ui.md`
- `docs/concepts/idempotency.md`
- `docs/demonstration.log`
- `docs/files-created.md`
- `docs/phase0-workspace-baseline.txt`
- `docs/phase1-results.md`
- `docs/system-inventory.md`
- `docs/verification.md`
- `docs/verification-probes/independent-results.json`
- `docs/verification-probes/independent_phase1.py`
- `docs/verification-probes/pytest.txt`
- `docs/verification-probes/resume-results.json`
- `docs/verification-probes/resume_after_adapter_error.py`
- `lab/__init__.py`
- `lab/__main__.py`
- `lab/adapters/__init__.py`
- `lab/adapters/bridge.py`
- `lab/adapters/modeling.py`
- `lab/adapters/observability.py`
- `lab/adapters/orchestration.py`
- `lab/adapters/quality.py`
- `lab/adapters/testing.py`
- `lab/adapters/workers/modeling.py`
- `lab/adapters/workers/observability.py`
- `lab/adapters/workers/orchestration.ts`
- `lab/adapters/workers/quality.py`
- `lab/adapters/workers/testing.py`
- `lab/cli.py`
- `lab/contracts.py`
- `lab/core.py`
- `lab/fixtures.py`
- `lab/learning.py`
- `lab/scenarios.py`
- `lab/store.py`
- `lab/telemetry.py`
- `lab/warehouse.py`
- `lab/web.py`
- `lab/web_assets/index.html`
- `lab/web_assets/style.css`
- `lab/web_assets/app.js`
- `pyproject.toml`
- `tests/contract/test_native_execution.py`
- `tests/contract/test_observability.py`
- `tests/contract/test_quality.py`
- `tests/contract/test_testing.py`
- `tests/e2e/test_cli.py`
- `tests/e2e/test_web.py`
- `tests/integration/test_pipeline.py`
- `tests/unit/test_foundations.py`
- `uv.lock`

Ignored run artifacts live under `.lab/`; the default demonstration contains the real SQLite warehouses, native metadata database, event exports and immutable snapshot references.
- `docs/browser-ui-verification.md` — browser UI check results and saved preview.
- `docs/screenshots/browser-ui-desktop.jpg` — actual desktop browser preview.

Business exercise expansion:

- `lab/business_catalog.py` — ten original business fixtures, SQL, requirements, answer keys, and architecture tradeoffs.
- `lab/business.py` — bounded business coordinator and verified local snapshot publication.
- `lab/adapters/workers/business_modeling.py` — native generic SQL/key API adapter.
- `lab/adapters/workers/business_quality.py` — native arbitrary-grain contract adapter.
- `lab/web_assets/business-app.js` — exercise library, business questions, theory and evidence views.
- `tests/e2e/test_business_web.py` — all ten native learning journeys and compatibility/guard checks.
- `docs/business-exercises.md` — catalog, decision, scope and sources.
- `docs/business-exercises-verification.md` — implementation check evidence.
