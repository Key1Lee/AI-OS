# Step 3 file manifest

All paths below are inside AE Lab. This manifest describes Step 3 work relative
to the existing Step 1/2 workspace, which already had uncommitted changes.

## Added

| File | Purpose |
|---|---|
| `curriculum/business-bank.json` | 60 original cases, private assessment contracts and pinned references |
| `curriculum/business-paths.json` | Ten prerequisite-aware areas and initial professional level |
| `lab/reasoning_fixtures.py` | Synthetic domain data and explicit fixture calculations |
| `lab/business_reasoning.py` | Stateless objective checks, typed policies, join traces and evidence-backed review validation |
| `lab/web_assets/reasoning.js` | Business workbook renderer in the existing `/learn` page |
| `scripts/build_business_bank.py` | Original case authoring source and deterministic bank builder |
| `scripts/validate_business_bank.py` | Contract, fixture, negative-answer and three-mode acceptance harness |
| `tests/learning/test_business_reasoning.py` | Business sentinels, disclosure, semantic review, routing, recall and persistence tests |
| `docs/business-reasoning.md` | Architecture, coverage, launch commands, tutor workflow and limits |
| `docs/business-reasoning-files.md` | This manifest |
| `docs/business-reasoning-verification.md` | Observed checks and limitations |
| `docs/business-reasoning-validation.json` | Machine acceptance receipts for all 60 definitions |
| `docs/business-progress-preservation.json` | Before/after hashes proving old local progress was retained |
| `docs/business-first-session.json` | First authentic session handoff; no learner answers |
| `docs/screenshots/business-reasoning-feedback.png` | Isolated browser proof of tutor review and multiplicity evidence |
| `docs/screenshots/business-first-session.png` | Initial authentic challenge with answers withheld |

## Extended

| File | Change |
|---|---|
| `contracts/problem.schema.json` | Add `reasoning` kind without changing existing definitions |
| `curriculum/curriculum.json` | Add 40 business concepts and link the learning paths |
| `curriculum/coverage-matrix.json` | Regenerate authored availability; no learner-state write |
| `lab/problems.py` | Load the new bank, validate its references and protect disclosure |
| `lab/learning_engine.py` | Questions, evidence variants, structured submissions and trusted tutor review in the same coordinator |
| `lab/mastery.py` | Focus-relevant selection, prerequisite preference and L3 reasoning entry |
| `lab/learning_cli.py` | Focus filters and trusted stakeholder-response command |
| `lab/web.py` | Focus query parameters and one renderer asset; retain existing session API |
| `lab/web_assets/learning.html` | Practice focus selector and reasoning renderer inclusion |
| `lab/web_assets/learning.js` | Dispatch the existing renderer, preserve drafts and show compact source timestamps |
| `lab/web_assets/learning.css` | Workbook, conversation and responsive source-table presentation |
| `tests/learning/test_contracts.py` | Retain the 116-new-SQL budget and add the exact 60-case reasoning budget |
| `tests/learning/test_sql_engine.py` | Keep SQL-only parameterization scoped to SQL/debug when reasoning joins the catalog |
| `tests/learning/test_web.py` | Focus, reasoning actions and absence of public tutor-approval endpoints |
| `README.md`, `docs/architecture.md` | Explain the integrated extension and entry points |

`.lab/step3-baseline.json` is a local progress baseline. UI verification profiles
under `.lab/business-ui-*` contain synthetic QA activity, separate from the real
profile. No learner answers or tests were injected into the real profile.
No dependency, SQL executor, sibling project or shared AI-OS change was needed.
