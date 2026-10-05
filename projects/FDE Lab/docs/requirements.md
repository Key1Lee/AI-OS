# Phase 1 scope and acceptance

Contract source: the user's [Forward Deployment Engineering Lab master prompt](master-prompt.md), especially sections 56–63 and 75–79, supplied 2026-10-03. The original brief is preserved here as project-owned requirements.

Build one local, resumable Northstar engagement. Own customer simulation, evidence disclosure, learner state, diagrams, box exploration, active recall, and evidence-backed progress. Reference existing AI-OS/data/testing capabilities without importing, copying, executing, or altering them. Avoid new infrastructure and a broad curriculum.

| Requirement | Observable evidence |
|---|---|
| Ambiguous opening, no diagnosis | Opening output; unreleased evidence cannot be read |
| Only requested stakeholder context | One configured topic per question; unknown questions preserve uncertainty |
| Learner reasoning and feedback | Saved submissions, rubrics, explicit attributed assessment |
| Architecture and technical depth | Current flow plus 11 explorable boxes |
| Bounded learner implementation | Broken SQL, synthetic fixture, independent oracle and varied regression cases |
| Failure and diagnosis | Separate broken replay branch, requested logs, learner debugging and re-test |
| Customer value | Approved target/baseline and synthetic pilot evidence; learner measurement |
| Recall/progress | Saved recall answers, concept relationships, conservative mastery evidence |
| Persistence/reset | Atomic locked writes, archived work, reproducible initial state/fixtures |
| Boundaries | Project-local code/state, reference-only integration registry |

Free-text semantic evaluation is tutor-assisted. The deterministic engine does not validate arbitrary prose. Real infrastructure deployment, cloud credentials, live LLM inference, external systems, broad industry scenarios, and production access enforcement are intentionally outside Phase 1. Synthetic targets are customer statements inside the scenario, not invented by learner grading.

Checks: `python3 -m unittest discover -s tests -v`. Independent verification maps these criteria to concrete observations in `docs/verification.md`.
