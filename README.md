# AI-OS

AI-OS is the top-level engineering system and shared architectural layer for
standards, templates, skills, commands, scripts, schemas, evaluations, and
architectural guidance.

## Project organization

Every directory inside `projects/` is an independent business project. New
projects belong at:

```text
projects/<project-name>/
```

Project-specific business logic, credentials, connections, tests, and
requirements must remain within the applicable project directory and must not
be added to the shared AI-OS layer.

## Shared model boundary

`py_dev/` provides a provider-neutral model router for Py.Dev workflows. It is
local-first and does not change the independent project runtimes. See
[AI-OS runtime](architecture/runtime.md) for configuration inheritance,
local Qwen startup, context and reasoning policy, and the CLI. See
[Model router architecture](architecture/model-router.md) for provider adapters
and fallback behavior.

## Shared Skills

Six reusable Skills live in the canonical [`skills/`](skills/) directory. See
[Skill architecture](architecture/skills.md) for activation, task profiles,
generated Codex/Claude mirrors, Qwen execution, and evaluations.

Completed-change verification follows [verification guidance](architecture/verification.md)
and existing project checks.

Completed-change review follows [review guidance](architecture/review.md)
and the affected project's contracts and checks.

Unexplained failures and root-cause requests follow [debug guidance](architecture/debug.md)
before a corrective change returns through verification.

Focused testing uses [repository test guidance](architecture/testing.md) and the
affected project's deterministic checks; verification decides overall acceptance.

Behavior-preserving structural work follows [refactoring guidance](architecture/refactoring.md)
within Implementation and returns through verification when preservation needs proof.

System transitions follow [migration guidance](architecture/migration.md) within Plan and
Implementation, with project-owned migration tools and independent verification.

Release readiness and delivery follow [release guidance](architecture/release.md),
using project-owned mechanics and explicit production authorization.

Active operational impact follows [incident guidance](architecture/incident.md):
assess impact, stabilize within authorization, and verify recovery.

Scoped vulnerability assessment follows [security-review guidance](architecture/security-review.md)
and validates realistic attack paths before remediation.
