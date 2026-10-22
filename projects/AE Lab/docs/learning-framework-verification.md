# Step 1 execution evidence — 2026-10-14 (Asia/Seoul)

Final implementation: `uv run pytest -q` → **137 passed in 119.51s**
(83 existing tests and 54 framework tests). No tests were skipped.

The final run includes the late older event arriving with a higher event ID,
downward amount revisions, native nonblocking source warnings, private fixture
and oracle version hashes, and isolation of learning-job metadata from the
original UI. Incorrect ordering by arrival time, event ID alone, or amount passes
the initial fixtures but fails the independent revision fixture. A warning test's
initial expectation was corrected from `FAIL` to the native Quality result
`WARN`; the final suite above includes that correction.

Final `node --check lab/web_assets/learning.js`, `git diff --check`, and registry
validation passed (10 systems). The rebuilt source distribution and wheel passed
an import outside the repository: seven validated problems, 446 concept IDs,
packaged schema and browser assets. The restarted server at
`http://127.0.0.1:8088/learn` visibly shows seven exercises and all six modes;
no learner exercise was started during that final check.

Earlier checkpoints follow for context.

Baseline, before changes: `.venv/bin/python -m pytest -q` → **83 passed in 113.91s**.

New framework: `uv run pytest -q tests/learning` → **46 passed in 10.76s**.

Full suite: `uv run pytest -q` → **129 passed in 110.13s**.

The new suite runs the three SQL problems and debugging repair against actual
PostgreSQL 17.11, four deterministic cases each. Model exercises invoke native
Modeling grain/key assertions. SQL output constraints use native Modeling and
Quality, and lineage receipts use native Observability. Spaced recall invokes
Toptal's native exact enforcement without writing its exam/mastery records.

Coverage includes initial and advanced disclosure; requirements/grain before SQL;
progressive hint limits and solution guards; correct clean/adversarial SQL;
deterministic ties; missing loan preservation; raw-event overcounting; wrong
declared grain even with correct numbers; actual join fanout; exact SQL errors;
review-required architecture; assisted evidence exclusion; reviewed understanding;
independent debugging/transfer; multi-day mastery gates; weak-concept selection;
real coverage gaps; persisted sessions/evidence; stale web actions; original
business catalog and routes.

`node --check lab/web_assets/learning.js` and `git diff --check` passed.
`uv build --out-dir .lab/step1-wheel` built the source distribution and wheel.
The availability matrix generator emitted **446 concept records** for 18 areas.

Read-only native integration probes returned an Orchestration SUCCESS trace with
retry/backfill simulation and a Semantic reference explicitly marked inapplicable
to the new scenario metrics. These are bounded synthetic interfaces, not live
production connections.

Browser verification uses `.lab/step1-ui-check`, separate from learner profiles.
The local browser was used to verify phase progression, source tables, requirements
capture, hidden solution behavior, narrow-screen overflow and draft preservation.
Screenshots and final registry checks are recorded after those checks complete.

After the browser fixes and CLI record guard, the focused run
`uv run pytest -q tests/learning tests/e2e/test_cli.py` passed **53 tests in 25.16s**.
After tightening advanced recommendation disclosure, the changed selection,
contract and web tests passed **25 tests in 3.44s**. The earlier full-suite result
is reported separately rather than presenting a later unexecuted total.

Registry check: `systems-registry/.venv/bin/python systems-registry/scripts/validate_registry.py`
(from AI-OS root) → **Registry validation passed: 10 system(s)**.

Wheel import outside the repository succeeded with seven validated problems,
446 concept IDs, packaged JSON Schema and browser assets.

Browser observations: at the narrow breakpoint, page width and scroll width
both measured 415px; at the desktop breakpoint, both measured 1305px. A draft
SQL answer remained intact after Hint 1. The actual failing query matched one
of four fixture cases; for L1, raw aggregation produced 64000 cents while the
independent expected value was 30000. No corrected SQL was revealed. Navigation
was enabled after the operation completed. Temporary viewport overrides were
reset and the isolated UI server was stopped.

Previews: [curriculum](screenshots/learning-curriculum.jpg),
[library](screenshots/learning-library.jpg),
[actual SQL feedback](screenshots/learning-feedback.jpg).
