# Toptal-Testing

Persistent practice and assessment for independent engineering competence.
This is an original preparation environment, not an official Toptal assessment
or a predictor of acceptance by any employer.

## Senior Analytics Engineering trainer — SQL release

Built 2026-10-01 as an additional local application. The working Phase 1 loop is:
**Continue Training → original SQL exercise → Monaco editor → Run in DuckDB →
Submit hidden tests → feedback → saved evidence → next recommendation**.
It includes adaptive selection, conservative mastery, mistakes, review dates,
practice filters, strict SQL interview practice, drafts and history. The original
FDE browser and terminal trainers documented below remain available.

**Launch:** double-click `Start-AE-Trainer.command`, or run it from this project.
Open `http://127.0.0.1:8001` and keep the terminal running. Press Control-C to stop.
SQL training needs no API key and works offline after installation.

Prerequisites: macOS with `/usr/bin/sandbox-exec`, Python 3.11+, and Node.js
22.12+ with npm for the initial client build. Other operating systems can browse
content but SQL execution fails closed until an equivalent sandbox is added.

```bash
make setup
make dev
```

`make setup` installs project dependencies and builds the React/TypeScript client.
The launcher also performs initial setup if needed. A single FastAPI process
serves the built UI and API. For frontend development, run `npm --prefix apps/web
run dev` alongside `make dev`; Vite proxies `/api` to port 8001. No CDN assets are
needed at runtime. Vite replaces the preferred Next.js here to keep offline local
startup to one process; the UI still uses React, TypeScript and Monaco.

Operational evidence is separate: `data/ae-trainer.db`, initialized by Alembic
and seeded automatically without resetting attempts. Export/backup the stopped
SQLite database before manual migrations; do not overwrite the canonical
assessment registers with application test results. Override the profile path
using `AE_TRAINER_DB`. `AE_SQL_TIMEOUT` defaults to 5 seconds per query/case;
output is limited to 1,000 rows and DuckDB memory to 128 MB. See `.env.example`.

Verification commands:

```bash
make test
make lint
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/playwright" \
  npm --prefix apps/web exec -- playwright install chromium
make test-e2e
```

Tests and browser smoke runs use temporary profiles; they do not create learner
mastery. `make seed` validates and inserts new exercise versions idempotently.
No reset command is supplied because deleting evidence should be intentional;
use `AE_TRAINER_DB` for a fresh separate profile instead.

The bank contains **12 original SQL problems**, each with a public fixture and
three hidden categories, covering join fanout, deduplication, NULLs, ties, UTC
dates, ratios, rolling windows, retention, temporal ownership and event sequences.
Different deduplication scenarios test transfer. Exercise versions are frozen;
the same problem, viewed solutions, hints and retries cannot earn new independent
credit. Senior levels require harder evidence, different contexts and cold retests.

The dashboard provides Continue Training, Practice, SQL Interview, Competency
Map, Mistake Review, Review Queue, Exercise Library and Session History. The
solving screen shows the problem and table previews beside the editor, with
query output and submission review beneath it. Light and dark appearances and
narrow layouts are supported.

Later dbt labs, reasoning exercises/LLM evaluation, mixed interviews, take-home
projects and the 75–120 exercise expansion **remain planned**. They are clearly
identified in Labs & Take-Home and are not presented as working or evaluated.
Deterministic SQL works without a model. Explanation quality is stored but
unassessed; no lexical or LLM guess substitutes for execution.

Documentation: [architecture](docs/architecture.md), [implementation plan](docs/implementation_plan.md),
[public research](docs/research/2026-10-01-public-curriculum.md),
[adding exercises](docs/adding_exercises.md), [scoring](docs/scoring.md),
[mastery](docs/mastery.md), [interview mode](docs/interview_mode.md),
[dbt lab boundary](docs/dbt_lab.md), [API contract](docs/api.md),
and [verification results](docs/verification.md).

Troubleshooting: keep the launching terminal open; use port 8001 for this trainer
and 8000 for the FDE app. A sandbox/startup error keeps submissions saved without
awarding or removing mastery. Fix the environment and retry the saved request.
After a process interruption, an in-flight submission's short execution lease
must expire before retry. On a stale draft conflict, reload the saved version;
the browser retains its unsynced copy for explicit restoration. To rebuild after
source changes, run `npm --prefix apps/web run build` and restart the trainer.

## Data System Map — first vertical slice

Added 2026-10-02 to the same local application. Open **Data System Map** in trainer
navigation or visit `http://127.0.0.1:8001/map` for the full trainer investigation view.
Use the existing launcher or `make dev`. `make setup` installs the sibling
[Data Observability System](<../Data Observability System/README.md>) package and UI
dependencies; no API key is required. The independent generic app runs on port 8002.

The default five-stage overview expands into focused model lineage. Select a
node for schema, declared grain, direct neighbors, recorded tests, execution
results, SQL text, evidence and business-output impact. Import a local dbt
manifest with optional run results, catalog and freshness artifacts. Imports are
atomic; missing metadata remains unknown and provenance is inspectable.

The original synthetic commerce example includes a real DuckDB-generated grain
error. Learning shows evidence-supported suspicion and uncertainty. Choose
**Start Assessment before exploring** for a first independent investigation;
assessment hides automated cause labels and hints while logging explicit
inspections. Diagnosis drafts, candidate hypotheses, ordered actions and results
persist. Eight objective answer/action checks do not prove a repair or broad
mastery; inspecting recorded tests is not executing dbt. These sessions do not
update the canonical assessment registers or existing SQL competency records.

Generic metadata snapshots now use `../Data Observability System/data/observability.db`
(or the generic `OBSERVABILITY_DB` override); investigation evidence uses
`data/data-map-training.db`. An `AE_TRAINER_DB` override gives both separate sibling
profiles. Browser tests use disposable profiles. Stop the process before copying
SQLite profiles for backup, retaining associated WAL files if present.

Column lineage, SQLGlot/SQLFluff analysis, natural-language query translation,
live AI reasoning, further adapters and warehouse/runtime connections remain
later slices. The UI reports unavailable lineage without fabricating edges.

Checks: `make test`, `make lint`, `npm --prefix apps/web run build`,
`make test-e2e`, `make check-map-demo`. See [migration and trainer policy](docs/data-observability-migration.md),
[Observability boundary](<../Data Observability System/README.md>),
[shared APIs](<../Data Observability System/docs/api.md>),
[artifact research](<../Data Observability System/docs/initial-implementation/research.md>)
and [migration verification](<../Data Observability System/docs/verification.md>).

## Project state

Initialized on 2026-09-26 at `/Users/key/_AI-OS/projects/Toptal-Testing/`, using
the existing Core location explicitly selected by the user. No prior project,
assessment attempts, tests, or competency evidence were found at initialization.
The project and Core were not Git repositories. No application dependencies,
runtime, or schedules were introduced.

The default starting emphasis is Forward Deployed AI/Data engineering, alongside
the user's target roles: Forward Deployed Engineer, Forward Deployed AI Engineer,
Analytics Engineer, Data Engineer, AI/Data Solutions Engineer, Technical Solutions
Engineer, and Workflow Automation Engineer. Adapt emphasis to the user's current
target role and observed results. Do not assume a single tool defines seniority.

## Authoritative records

- [Competency map](assessment/competency-map.md): current state and next selection.
- [Assessment history](assessment/history.md): attempts, actual assistance, results,
  remediation, retest status, and progress over time.
- [Weaknesses](assessment/weaknesses.md): evidence-backed unresolved gaps and practice.
- [Mastery evidence](assessment/mastery-evidence.md): independent demonstrations,
  verification, and regressions.

Use stable assessment IDs such as `A-001`, gap IDs such as `W-001`, and mastery
record IDs such as `M-001`. Link related records instead of copying answers or
maintaining competing competency scores. Preserve prior evaluations; append a
dated correction with its reason if an evaluation changes. Persist enough of the
challenge, submitted work, probes, and feedback to audit a meaningful assessment.
Create an attempt artifact only when an assessment starts and needs one.

## Operating cycle and selection

ASSESS → RECORD EVIDENCE → IDENTIFY GAPS → PRACTICE → RETEST → VERIFY MASTERY
→ INCREASE DIFFICULTY. This cycle operates through user sessions; it does not
authorize background scheduling or notifications.

Select the next challenge using unresolved high-impact weaknesses first, then
target-role importance, due retests, untested competencies, maintenance of
demonstrated skills, and harder combinations of established skills. Avoid random
practice when evidence suggests a higher-value assessment.

Difficulty levels are 1 Fundamentals, 2 Applied Fundamentals, 3 Production
Engineering, 4 Senior Engineer, and 5 Staff / Expert Screening. Progress requires
performance evidence. Reduce difficulty when foundational gaps would otherwise
make a harder exercise uninformative.

## Modes and assessment conduct

- **Baseline:** sample high-value competencies sufficiently to identify meaningful
  strengths and gaps, without testing every topic at once.
- **Screening — `Start Screening`:** consult the records, select one original
  challenge, then probe until there is enough evidence for a fair evaluation.
- **Debugging:** evaluate observed versus expected behavior, hypotheses, evidence,
  root cause, fix, validation, and prevention. Score troubleshooting discipline
  separately from eventually finding the answer.
- **System Design:** supply a business problem without supplying its architecture.
  Evaluate relevant requirements, contracts, state, tradeoffs, failure handling,
  security, operations, and simplicity.
- **Project:** assign an original end-to-end problem with realistic constraints
  and incomplete information. Assess clarification, implementation, verification,
  documentation, and technical defense.
- **Review:** after an attempt, identify correct work, meaningful weaknesses,
  underlying concepts, knowledge gaps versus execution mistakes, remediation,
  and whether a retest is required.
- **Retest:** use a materially different problem and, where relevant, a different
  technical surface to test the same underlying competency independently.

Before an attempt, establish the objective, difficulty, allowed tools, assistance
mode, relevant evaluation dimensions, and completion conditions. Default to an
UNAIDED diagnostic; allow clarification of requirements without treating it as
solution assistance. Log hints, solution help, and AI use actually supplied or
reported, and qualify independence accordingly. Assistance is allowed when the
user asks; it changes the interpretation of the evidence.

Keep assessment and learning distinct: probe first, then evaluate and teach after
the attempt concludes. Do not disclose a solution prematurely. Freeze scenario
facts and acceptance criteria before testing, answer discoverable questions
consistently, and do not invent retroactive constraints to make the learner fail.
For complex simulations, fix any planned twists before the attempt. A local
assessment file is not a security boundary for an answer key; do not claim otherwise.

Prefer realistic data, integration, deployment, debugging, and customer problems
over trivia. Use algorithms when the competency warrants them. Test whether AI
is needed; prefer deterministic software for deterministic work. Assess the
simplest solution that satisfies the stated requirements.

## Evidence and evaluation

Evaluate only relevant dimensions: correctness, decomposition, implementation,
SQL/Python/API knowledge, debugging, system design, testing, reliability, security,
requirements, business understanding, communication, judgment, independence,
and production readiness. Use observable artifacts and decisions.

Significant failures may be classified as Knowledge Gap, Reasoning Gap,
Implementation Error, Debugging Process Gap, Architecture Gap, Communication
Issue, Requirements Gap, or Avoidable Oversight. Explain the classification with
evidence. Do not inflate scores or infer a general weakness from an untested area.

Mastery requires independent demonstrated performance at a stated scope and
difficulty. Reading a solution does not establish mastery. After remediation,
require a materially different retest. Reopen a competency if later evidence
shows regression; retain the earlier evidence and the reason for reopening.

## Research provenance and current-process claims

The user's initialization request is the controlling source. The supplied
`/Users/key/Downloads/deep-research-report (3).md` is supporting research only.
Its SHA-256 at initialization was
`7e72a363f13a56f845233da3cacf2eba84b87691feb4af4f29a42789ebe742aa`.
It discusses an FDE specialization and internal preparation gates, but its
embedded citation IDs and `sandbox:` package links were not independently
resolved. Referenced PDFs, JSON packages, and their claimed verification were
not supplied as accessible project artifacts. Do not record them as inspected.

No numerical weights or Gates A–E have been adopted as official Toptal policy.
Research and prior assistant-created project work are not learner performance
evidence. On **`Refresh Toptal Process`**, research current public information,
prefer official Toptal sources, and use recent candidate reports only as secondary
evidence. Distinguish documented facts, unofficial observations, internal design,
and uncertainty. Do not seek proprietary content or change the model without evidence.

## Initialization verification

This initialization adds instructions and empty evidence registers only. Inspect
Markdown links and record consistency; there is no application unit, integration,
regression, or end-to-end suite to run. Add exercise checks only when a concrete
assessment requires them, and distinguish the learner's checks from a grader.

## Local interactive application

The project now includes a local browser application that implements the
assessment workflow without changing the canonical evidence rules above.

### Launch on macOS

1. Configure the shared AI-OS provider environment in Terminal. OpenAI calls
   require the central credential, `AI_OS_PROVIDER_OPENAI_ENABLED=true`,
   `ALLOW_OPENAI=true`, and a positive `CLOUD_CALL_BUDGET`. Do not put credentials
   in this project or an assessment record.
2. Double-click `Start-Toptal-Testing.command` in Finder.
3. Keep the opened Terminal window running while using the browser application
   at `http://127.0.0.1:8000`.
4. Press Control-C in that Terminal window when finished.

The launcher resolves its own directory, creates `.venv` when needed, installs
the dependencies in `requirements.txt` when they change, binds Uvicorn only to
`127.0.0.1`, waits for `/api/health`, and opens the default browser. If the API
provider is unavailable, the application reports that state and preserves saved
submissions. The launcher does not collect or store provider credentials.

### Runtime architecture

```text
Browser (HTML/CSS/vanilla JavaScript)
  -> FastAPI state and integrity boundary
  -> shared AI-OS typed provider boundary
  -> structured interviewer proposal
  -> deterministic assessment engine
  -> SQLite operational state
  -> completed-module evidence synchronization
```

The default interviewer model is `gpt-6-sol` with `medium` reasoning. Module
evaluations, Level 4+ work, system design, architecture defense, and production
debugging use `high`. Override the centralized defaults with
`TOPTAL_TESTING_MODEL`, `TOPTAL_TESTING_REASONING`, and
`TOPTAL_TESTING_HIGH_REASONING`.

The backend supplies its Pydantic domain schema to the shared AI-OS provider
boundary. AI-OS owns client creation, credentials, budget reservation, provider
audit, typed parsing, and bounded session recovery. Installing `requirements.txt`
installs the local shared package with `-e ../..`. The
model proposes interviewer content and evidence updates; application code owns
state transitions, assistance floors, feedback visibility, difficulty bounds,
idempotency, and persistence. Candidate submissions are stored before a model
call. Retrying the same request ID cannot create a duplicate turn.

### Local records

- Operational session state: `data/assessment.db` (ignored by Git).
- Human-readable completed-module artifacts: `assessment/session-evidence/`.
- Canonical progress: `assessment/competency-map.md`.
- Attempt ledger: `assessment/history.md`.
- Evidence-backed gaps: `assessment/weaknesses.md`.
- Mastery: never awarded automatically by this first application version;
  `assessment/mastery-evidence.md` remains governed by the independent,
  scoped, verified-evidence rules above.

No Markdown evidence changes are made for an active or paused module. A completed
module is synchronized through an idempotent application-controlled path. An
assisted demonstration is capped at DEVELOPING even if a model proposes
DEMONSTRATED.

### Development checks

```bash
.venv/bin/python -m pytest -q
zsh -n Start-Toptal-Testing.command
```

Tests use temporary project copies and a deterministic fake interviewer. They do
not change real learner evidence or require an API key.

## Terminal training system

`START_TOPTAL_TRAINING.command` launches a separate adaptive terminal workflow.
It does not replace the browser assessment app and it never writes to the four
canonical Markdown evidence registers. Training estimates are deliberately kept
in `data/training.db`; they are practice signals, not verified hiring evidence.

Double-click the launcher in Finder, or run:

```bash
./START_TOPTAL_TRAINING.command
```

Press Enter at the menu for the recommended Daily Training session. Other modes
are Cold Recall, Practice, Assessment, Mock Interview, Weakness Review, and
Progress. Enter multi-line answers directly in Terminal and finish each response
with `/submit`. `/pause` safely stops a session; the next launch offers recovery.
Daily and Practice modes accept `/hint`. Assessment, Mock Interview, and Cold
Recall reject and audit hint requests.

### Training architecture

```text
Terminal UI (`training.application`)
  -> deterministic selector and original scenario combinator
  -> answer-first durable persistence (`data/training.db`)
  -> authoritative deterministic checks
  -> local Qwen semantic/reasoning evaluation (default when healthy)
  -> optional structured GPT-5.6 Sol evaluation (explicit selection)
  -> conservative lexical rubric fallback (last resort)
  -> mastery state machine + weakness registry + spaced review schedule
```

The application covers Python semantics/design, SQL, data modeling, distributed
systems, API integration, reliability, incident response, testing, debugging,
delivery, ambiguity, decisions, and learning/correction. Scenarios combine a
curated technical contract with reproducible business-domain and operational
constraints so launches do not depend on a single fixed prompt. Content can be
extended in `training/content/questions.json` without changing orchestration.

The default `EVALUATOR_PROVIDER=auto` probes the configured local OpenAI-compatible
endpoint and uses Qwen when healthy. This project defaults to
the shared AI-OS loopback endpoint, `http://127.0.0.1:8080/v1`, and shared
`QWEN_MODEL` configuration. If no alias is configured, the central transport
discovers a Qwen alias from the served model list. Provider credentials,
transport and retries live in AI-OS; the deprecated local API-key field is not
read from the environment. The application validates the model's JSON against a strict Pydantic schema.
A timeout, connection failure, incomplete rubric evidence, or malformed response
is rejected and visibly falls back to conservative lexical evaluation.

Set `EVALUATOR_PROVIDER=openai` and export `OPENAI_API_KEY` to make GPT-5.6 Sol the
primary evaluator, with shared `AI_OS_PROVIDER_OPENAI_ENABLED`, `ALLOW_OPENAI`
and positive `CLOUD_CALL_BUDGET` also required. The local Qwen provider remains its runtime failover when
healthy. OpenAI uses the Responses API with structured output: medium reasoning
normally and high reasoning for difficulty 4+, Assessment, and Mock Interview.
Set `EVALUATOR_PROVIDER=offline_fallback` (or the legacy
`TRAINING_LLM_MODE=off`) to force lexical evaluation. `TRAINING_LLM_MODE=required`
retains the prior safe-pause behavior when no configured reasoning evaluator can
complete. See `.env.example`; never store a real key in the project.

Every attempt first receives deterministic checks. Authoritative failures cap the
final result even if a reasoning model returns a pass. The current curated bank is
prose-answer based, so its built-in objective checks cover answer and rubric
contract validity; executable SQL/code exercises still require future sandboxed
fixtures before row-level or unit-test validation can be claimed. Qwen evaluates
semantic correctness, assumptions, decomposition, tradeoffs, engineering judgment,
production readiness, reliability, observability, security, data quality, business
understanding, communication, and edge cases. It must cite demonstrated evidence
and cannot award credit for terminology alone.

Evaluation audit records are stored separately in `evaluation_runs`, including
provider, model, rubric version, deterministic results, structured result,
timestamp, and fallback reason. `training.calibration.evaluate_for_calibration`
can explicitly run a saved answer through multiple supplied providers and retain
each result independently; it never averages scores or changes primary mastery.

Mastery is harder to earn than a single pass. The state machine requires multiple
independent successes, a later cold recall, transfer across distinct scenario
families, and no unresolved evidence deficit before `MASTERED`. Hinted success is
recorded separately and follow-up answers do not inflate independent mastery.
Default review intervals are 1 day after failure, 3 after hinted success, 7 after
independent success, 14 after cold recall, and 30 after transfer; repeated failures
shorten the next interval to 12 hours.

Terminal lexical results are **unassessed practice coverage**. They retain the
answer, rubric coverage, feedback, assistance and evaluator audit, but cannot
change assessed success, mastery, failure streaks, cold/transfer/family credit or
success spacing. Practice uses the existing short failure/practice interval
(one day by default). Recognized, complete structured reasoning metadata keeps
the existing assessment policy, with no new confidence cutoff. Genuine
authoritative deterministic failures still count as failures. Follow-ups and
secondary calibration stay diagnostic. Session summaries separate assessed
outcomes from unassessed/diagnostic attempts; exposure counts remain available.

Changing the policy does not repair historical aggregates automatically. The
terminal marks pre-policy competency credit as `LEGACY`/unverified until an
explicit rebuild has reviewed it. The project-owned tool defaults to a read-only,
noninitializing preview with an explicit database path:

```sh
.venv/bin/python scripts/rebuild_training_credit.py --database /absolute/path/synthetic-copy.db
```

Preview a quiescent profile or a consistent backup/copy: the tool refuses a WAL
file rather than ignoring uncheckpointed evidence or creating SQLite side files.
It supports existing schema 2 only, at most 10,000 rows per evidence table and
64 MiB of profile/evidence. Unknown legacy metadata supplies no invented credit;
unreconstructable identity/time/mode/review records block apply. The preview
shows before/after derived values, unverified records and a `source_digest`.

After reviewing that concrete preview, an explicitly authorized state repair
uses `--apply --expected-digest <source_digest>`; `--backup <new-file>` optionally
selects its backup destination. Apply locks writers, recomputes and checks the
reviewed digest, takes a consistent SQLite backup under the same writer lock,
and atomically changes only competency/current-review summaries. It appends a
correction receipt to an existing session; it never rewrites attempts, evaluation
runs, historical review schedules or prior receipts, and never dates an old
assessment as passed today. Repeating an already current apply is a no-op.
Historical schedule rows remain evidence; the competency's `next_review_at` is
the current review pointer. Restore the recorded pre-repair backup with writers
stopped if state repair must be undone. No real learner profile is read or
rewritten by the development tests.

Terminal-system checks:

```bash
.venv/bin/python -m pytest -q tests/training
zsh -n START_TOPTAL_TRAINING.command
TRAINING_LLM_MODE=off TRAINING_DB=/tmp/toptal-training.db \
  .venv/bin/python -m training.cli
```
