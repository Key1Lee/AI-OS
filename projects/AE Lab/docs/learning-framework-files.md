# Step 1 file inventory

All implementation and business/learner state remain inside the existing AE Lab project.
Shared changes are limited to its ownership/dependency documentation.

Branch: `codex/ae-lab-grain-interviews`.

## Created

- [contracts/__init__.py](../contracts/__init__.py)
- [contracts/problem.schema.json](../contracts/problem.schema.json)
- [curriculum/__init__.py](../curriculum/__init__.py)
- [curriculum/coverage-matrix.json](../curriculum/coverage-matrix.json)
- [curriculum/curriculum.json](../curriculum/curriculum.json)
- [curriculum/policy.json](../curriculum/policy.json)
- [docs/learning-framework-files.md](../docs/learning-framework-files.md)
- [docs/learning-framework-verification.md](../docs/learning-framework-verification.md)
- [docs/learning-framework.md](../docs/learning-framework.md)
- [docs/screenshots/learning-curriculum.jpg](../docs/screenshots/learning-curriculum.jpg)
- [docs/screenshots/learning-feedback.jpg](../docs/screenshots/learning-feedback.jpg)
- [docs/screenshots/learning-library.jpg](../docs/screenshots/learning-library.jpg)
- [lab/adapters/workers/learning_modeling.py](../lab/adapters/workers/learning_modeling.py)
- [lab/adapters/workers/sql_modeling.py](../lab/adapters/workers/sql_modeling.py)
- [lab/adapters/workers/sql_observability.py](../lab/adapters/workers/sql_observability.py)
- [lab/adapters/workers/sql_orchestration.ts](../lab/adapters/workers/sql_orchestration.ts)
- [lab/adapters/workers/sql_quality.py](../lab/adapters/workers/sql_quality.py)
- [lab/adapters/workers/sql_semantic.py](../lab/adapters/workers/sql_semantic.py)
- [lab/curriculum.py](../lab/curriculum.py)
- [lab/learning_cli.py](../lab/learning_cli.py)
- [lab/learning_engine.py](../lab/learning_engine.py)
- [lab/mastery.py](../lab/mastery.py)
- [lab/problems.py](../lab/problems.py)
- [lab/sql_lab/__init__.py](../lab/sql_lab/__init__.py)
- [lab/sql_lab/catalog.py](../lab/sql_lab/catalog.py)
- [lab/sql_lab/contracts.py](../lab/sql_lab/contracts.py)
- [lab/sql_lab/datasets.py](../lab/sql_lab/datasets.py)
- [lab/sql_lab/evaluator.py](../lab/sql_lab/evaluator.py)
- [lab/sql_lab/integrations.py](../lab/sql_lab/integrations.py)
- [lab/sql_lab/oracles.py](../lab/sql_lab/oracles.py)
- [lab/sql_lab/postgres.py](../lab/sql_lab/postgres.py)
- [lab/web_assets/learning.css](../lab/web_assets/learning.css)
- [lab/web_assets/learning.html](../lab/web_assets/learning.html)
- [lab/web_assets/learning.js](../lab/web_assets/learning.js)
- [scripts/curriculum_inventory.py](../scripts/curriculum_inventory.py)
- [scripts/postgres_local.py](../scripts/postgres_local.py)
- [tests/learning/__init__.py](../tests/learning/__init__.py)
- [tests/learning/conftest.py](../tests/learning/conftest.py)
- [tests/learning/test_contracts.py](../tests/learning/test_contracts.py)
- [tests/learning/test_execution.py](../tests/learning/test_execution.py)
- [tests/learning/test_mastery.py](../tests/learning/test_mastery.py)
- [tests/learning/test_web.py](../tests/learning/test_web.py)

## Modified

- [README.md](../README.md)
- [docs/architecture.md](../docs/architecture.md)
- [docs/system-inventory.md](../docs/system-inventory.md)
- [lab/cli.py](../lab/cli.py)
- [lab/web.py](../lab/web.py)
- [lab/web_assets/index.html](../lab/web_assets/index.html)
- [lab/adapters/bridge.py](../lab/adapters/bridge.py)
- [pyproject.toml](../pyproject.toml)
- [uv.lock](../uv.lock)

## Shared map/registry

- `/Users/key/_AI-OS/SYSTEMS.md`
- `/Users/key/_AI-OS/systems-registry/registry/analytics-engineering-lab.yaml`

## Local runtime and verification artifacts

Ignored `.lab/` profiles contain the dedicated PostgreSQL cluster/socket/config, disposable UI-check profile, wheel build logs and an availability/probe profile. Earlier unfinished expansion drafts were preserved in `.lab/deferred-expansion/` when scope narrowed; they are not part of the delivered catalog or tracked implementation.

No sibling engine source, canonical Toptal learner record, unrelated project, shared runtime/router, or Skill was modified.
