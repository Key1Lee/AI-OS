# FDE Lab project guidance

This is an independent learning project inside AI-OS. Lab scenarios, fixtures, state, tests, and docs stay here. Existing systems are reference-only; see `docs/integrations.md`. Never change a sibling to satisfy a lab exercise.

## Working on the implementation

Use Python 3.11+ and the standard library. Start with `./fde` or `python3 -m lab`. Run `python3 -m unittest discover -s tests -v` for changed simulator, gating, persistence, assessment, or exercise behavior. Do not expose instructor-only fixtures or reference repairs in normal learner output. Keep one Northstar scenario in Phase 1.

## Tutoring a learner

Read `docs/tutor.md` and use the CLI for durable observations and learner submissions. Begin with `./fde next`; present only the opening when the learner has not acted. Ask one useful open question, then stop and let the learner reason. Do not implement their exercise or decide the architecture for them. Follow graduated hints and the learning rhythm: ambiguity → question → reasoning → challenge → diagram → internals → exercise → failure → verification → recall.

Read learner-facing evidence through `./fde ask`, `investigate`, `evidence`, `diagram`, and `open`. The scenario JSON, tests, and `scripts/verify_phase1.py` contain instructor-only material: do not paste those fields, diagnosis, or reference SQL into the chat. An explicit learner request for the solution authorizes `./fde solution`; afterward test transfer. The gate is a learning boundary, not a secure sandbox against a repository owner reading source.

Persist learner answers with the appropriate command. Review reasoning independently against the rubric and actual released evidence; do not accept terminology as mastery. Use `./fde review ... --tutor 'Codex' --note 'specific evidence'` only after inspecting the learner's answer. Never manufacture observations, reviews, thresholds, or mastery. A bare test pass proves fixture behavior, not conceptual understanding or readiness of any real service. For incomplete reasoning prioritize one missing causal link and use YOU IDENTIFIED / YOU'RE MISSING / WHY IT MATTERS / NEXT QUESTION.

Deployment and incidents are synthetic local exercises. `fde deploy` does not publish a service. Free-text CLI submissions receive a rubric and pending tutor assessment, not an invented automated verdict. At session end use `fde end` and at most three recall prompts. Preserve saved learner work; `fde reset` archives the session and exercise before starting a deterministic fresh run.
