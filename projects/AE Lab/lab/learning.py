"""One concept at a time; prompts remain separate from the grading contract."""

STEPS = (
    "orient", "predict", "run", "observe", "diagnose", "fix", "verify", "recall", "connect"
)

ORIENT = """Follow one order from source to dashboard.

SOURCE → LOAD → MODELS → QUALITY → REVENUE → DASHBOARD
          ↑
     ORCHESTRATOR

The source contains 1,000 orders. The loader writes them to the warehouse.
The orchestrator decides when to run and retry that work. Models turn loaded
orders into revenue; quality checks whether those rows satisfy their contract.
Observability connects the recorded failures to the outputs that depend on them.

Focus: what happens when a write succeeds only partly and the task runs again?
"""

PREDICT = """A loader writes 700 of 1,000 orders and crashes. Its retry starts from
the beginning and inserts all 1,000 source rows. It does not remove earlier rows.

Before running: how many rows will the warehouse contain?
"""

DIAGNOSE = """Read the observed counts, quality results and retry trace.

Which layer first changed the data incorrectly?
Which architectural property was missing?
Which quality signal supports that diagnosis?

You may record a short explanation alongside your selections.
"""

RECALL = """Use the recovered run to answer three short questions.

1. The repaired loader receives the same 1,000 orders again. How many rows remain?
2. Which source field should identify the same order across retries?
3. Which write operation can update an existing order or insert a new one?
"""

CONNECT = """Idempotency means repeating an operation preserves its intended result.

RETRY / BACKFILL → STABLE ORDER KEY → UPSERT → QUALITY → TRUSTED REVENUE

The orchestrator owns whether a retry runs; the loader owns safe repeated writes.
Models carry the resulting data into metrics. Quality detects duplicate keys.
Observability records the failed and recovered evidence and traces business impact.

Explain the path from one order to the dashboard from memory. This exercise
checks a narrow concept; repeated or assisted answers do not prove broad mastery.
"""
