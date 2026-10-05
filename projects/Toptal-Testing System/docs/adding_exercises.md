# Adding original SQL exercises

1. Copy the structure of a JSON file in `exercise_bank/sql`, using a new ID and
   an original business contract. Do not copy proprietary question banks.
2. Name the grain, eligibility, NULL rules, tie precedence, time boundaries and
   source guarantees. List exact output columns and the reference explanation.
3. Include one public fixture and hidden cases with independently authored
   expected rows. Include relevant dirty data and empty input. Each failing
   category needs a diagnostic probe that does not reveal its hidden rows.
4. Supply three progressively stronger hints and stable competency IDs. Cases
   may identify the subset of competencies they actually test. Include
   `sql.execution` so runtime-only failures have a scoped evidence destination;
   publish `expected_types` alongside output column names for schema checks.
5. Run `.venv/bin/python -m pytest -q tests/ae/test_contracts.py` and execute the
   reference query against every case with `SqlRunner.grade`.
6. Run `make seed`. Restart the app to load the revised bank.

Adding an exercise needs no engine change. Modifying any existing exercise
requires a version bump, including a prompt or expected-output edit. Attempts
retain their stored old version. Never update `exercise_versions` manually.

Add competencies to `curriculum/competencies.yaml` with unique IDs and acyclic
prerequisites. Relationships must reference known IDs. Uncovered competencies
remain unassessed. Selection weights are in `curriculum/selection.yaml`.

Example local validation (does not create learner evidence):

```python
from trainer.config import ROOT, Settings
from trainer.exercises.bank import Bank
from trainer.execution.sql import SqlRunner

exercise = Bank(ROOT).exercises["your-original-id"]
result = SqlRunner(Settings()).grade(exercise.reference_solution, exercise)
assert result["outcome"] == "Correct", result
```
