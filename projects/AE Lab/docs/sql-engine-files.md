# Step 2 file manifest

Changes are confined to AE Lab. Pre-existing shared and sibling changes were preserved.
Existing Step 1 schema/policy, adapters, Store and HTTP routes were reused.

## Created

- [curriculum/sql-bank.json](../curriculum/sql-bank.json)
- [curriculum/sql-dialects.json](../curriculum/sql-dialects.json)
- [scripts/validate_sql_bank.py](../scripts/validate_sql_bank.py)
- [tests/learning/test_sql_engine.py](../tests/learning/test_sql_engine.py)
- [docs/sql-problem-engine.md](../docs/sql-problem-engine.md)
- [docs/sql-engine-validation.json](../docs/sql-engine-validation.json)
- [docs/sql-first-session.json](../docs/sql-first-session.json)
- [docs/sql-engine-verification.md](../docs/sql-engine-verification.md)
- [docs/sql-engine-files.md](../docs/sql-engine-files.md)
- [docs/screenshots/sql-engine-browser.png](../docs/screenshots/sql-engine-browser.png)
- [docs/screenshots/sql-first-session.png](../docs/screenshots/sql-first-session.png)

## Extended

- [README.md](../README.md)
- [curriculum/curriculum.json](../curriculum/curriculum.json)
- [curriculum/coverage-matrix.json](../curriculum/coverage-matrix.json)
- [lab/problems.py](../lab/problems.py)
- [lab/mastery.py](../lab/mastery.py)
- [lab/learning_engine.py](../lab/learning_engine.py)
- [lab/learning_cli.py](../lab/learning_cli.py)
- [lab/sql_lab/contracts.py](../lab/sql_lab/contracts.py)
- [lab/sql_lab/catalog.py](../lab/sql_lab/catalog.py)
- [lab/sql_lab/datasets.py](../lab/sql_lab/datasets.py)
- [lab/sql_lab/bank_data.py](../lab/sql_lab/bank_data.py)
- [lab/sql_lab/bank_oracles.py](../lab/sql_lab/bank_oracles.py)
- [lab/sql_lab/oracles.py](../lab/sql_lab/oracles.py)
- [lab/sql_lab/evaluator.py](../lab/sql_lab/evaluator.py)
- [lab/sql_lab/postgres.py](../lab/sql_lab/postgres.py)
- [lab/sql_lab/integrations.py](../lab/sql_lab/integrations.py)
- [scripts/build_sql_bank.py](../scripts/build_sql_bank.py)
- [lab/web_assets/learning.html](../lab/web_assets/learning.html)
- [lab/web_assets/learning.js](../lab/web_assets/learning.js)
- [tests/learning/conftest.py](../tests/learning/conftest.py)
- [tests/learning/test_contracts.py](../tests/learning/test_contracts.py)
- [tests/learning/test_mastery.py](../tests/learning/test_mastery.py)
- [tests/learning/test_execution.py](../tests/learning/test_execution.py)
- [tests/learning/test_web.py](../tests/learning/test_web.py)
- [docs/architecture.md](../docs/architecture.md)
- [docs/learning-framework.md](../docs/learning-framework.md)

## Local runtime state

The existing `.lab/state.sqlite` contains the one untouched first live session and
its INTRODUCED events. Validation uses separate `.lab/sql-engine-validation` and
`.lab/sql-ui-verification` profiles. No learner attempts or successful mastery
evidence were inserted into the real profile. PostgreSQL and the loopback UI
remain running for that session.
