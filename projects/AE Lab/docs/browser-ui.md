# Local browser learning UI

Double-click `Start AE Lab.command` on the Desktop, or run:

```sh
uv run lab-web --open
```

The default URL is `http://127.0.0.1:8088`. Keep the launcher Terminal open.
Reopening the shortcut reuses this Lab's existing server. `--port` and
`--state-dir` allow isolated previews. CLI practice remains available.

## Reading and learning

The **Exercise library** contains ten original business cases plus the existing
retry exercise. New cases use distinct stories, source fixtures, faulty and
repaired SQL, verification criteria, and architectural explanations. See
[business exercises](business-exercises.md) for execution scope and sources.

- One active step follows ORIENT → PREDICT → RUN → OBSERVE → DIAGNOSE → FIX → VERIFY → RECALL → CONNECT.
- Click pipeline components for their input/output responsibility. Failure, impact and recovery get different colors and text labels.
- Prediction is submitted before evidence appears. Incorrect prediction still leads to observation.
- Diagnosis selects a layer, property and signal; optional prose is saved for reflection. Native evaluation checks the selections.
- Repair and verification invoke existing real adapters. Long operations show progress and disable repeated submissions.
- Evidence switches between baseline, failure, recovery and repeated retry. Counts, exact native money strings, attempts and incidents remain inspectable.
- Saved sessions resume the required operation, including an interrupted repair. A new exercise retains earlier evidence.
- Mobile uses a compact step strip and a scrollable pipeline. Desktop shows the full path and a focus card.

Staging/intermediate roles remain conceptual parts of the native model query;
the dashboard is a declared revenue consumer. Freshness is not measured.
Automated UI checks are assisted examples and cannot award learner mastery.

## Architecture decision

**Context:** Terminal practice preserves correctness but makes architecture harder to read.
**Decision:** Add a loopback Python standard-library HTTP server and local HTML/CSS/JavaScript
over the existing `Lab` coordinator. Share `.lab` state and native adapters. Keep assets offline.
**Alternatives:** A second learning engine or a framework/service stack.
**Tradeoffs:** One local user and one active operation at a time; no multi-user hosting.
**Consequences:** There is no duplicated SQL, quality, grading or incident engine. Both UI
and CLI retain the same data recovery gates. Session views provide progressive disclosure.

## API

| Route | Purpose |
|---|---|
| GET `/api/health` | Identify the local app and state profile |
| GET `/api/catalog` | Ten business case summaries, without answer keys |
| GET `/api/bootstrap` | Session list, write token and current operation identity |
| GET `/api/sessions/<run-id>` | Compact, disclosure-limited session view |
| POST `/api/sessions` | Create a fresh isolated exercise; optional `scenario_id` selects a business case |
| POST `/api/actions` | Submit run ID, expected step, action and structured answer |
| GET `/api/jobs/<job-id>` | Poll a native operation for its result or explicit failure |

Writes require the page's token, local Host/Origin, and current step. No endpoint accepts
arbitrary SQL or sibling paths. One worker serializes actions; mismatched steps and duplicate
operations cannot silently advance a session. Durable core state makes restart/resume safe.
The server binds only to `127.0.0.1` and is not intended for public hosting.

## Checks

`uv run pytest -q` includes the real native nine-step HTTP journey, progressive disclosure,
incorrect answers, repair gates, reload, reset retention, local request guards and required
resume operations. `node --check lab/web_assets/app.js` checks JavaScript syntax.
Browser checks cover actual forms, full recovery, saved-session reload and desktop/mobile layout.
