# AI-OS Agent Guidance

AI-OS is the top-level engineering system and shared architectural layer.

## Boundaries

- Treat each directory under `projects/` as an independent business project.
- Create future projects at `projects/<project-name>/`.
- Keep project-specific business logic, credentials, connections, tests, and requirements inside the relevant project directory.
- Do not place project-specific material in the shared AI-OS layer.
- Preserve existing files and directories. Inspect before changing, replacing, or deleting anything.
- When changing shared runtime or provider behavior, consult `architecture/runtime.md` and `architecture/model-router.md` as relevant.
- When changing a Skill, edit canonical `skills/<name>/` and use `scripts/sync_skills.py` to update generated Codex/Claude mirrors. See `architecture/skills.md` for the Skill boundary.
- For a request to verify a completed change, including `/verify`, follow `architecture/verification.md` and the affected project's checks. Keep verification independent from implementation and report evidence for each approved criterion.
- For a request to review a completed change, including `/review`, follow `architecture/review.md`. Inspect the changed code first, report only material evidence-supported findings, and keep review independent from implementation.
- For an unexplained failure or an explicit `/debug` request, follow `architecture/debug.md`. Establish expected versus observed behavior and causal evidence before handing a diagnosis to Plan or Implementation.
- For an explicit `/test` request or other focused testing task, follow `architecture/testing.md` and the affected project's test commands. Report reproducible evidence; leave the overall acceptance verdict to Verify.
- For AI-OS-wide architecture audits, use canonical `skills/audit/SKILL.md` and its bounded checker. Keep system Audit separate from review of a specific change.
- For an explicit `/refactor` request or meaningful structural cleanup, follow `architecture/refactoring.md` as behavior-preserving Implementation. Establish relevant invariants and evidence before claiming preservation.
- For an explicit `/migrate` request or a material version, schema, API, dependency, provider, or architecture transition, follow `architecture/migration.md` within Plan and Implementation. Keep production and destructive execution separately authorized.
- For an explicit `/release` request or release-readiness work, follow `architecture/release.md` and the affected project's release policy and tooling. Prepare a concrete candidate before seeking authorization for production-impacting actions.
- For an active or suspected material operational incident, including `/incident`, follow `architecture/incident.md`. Assess impact and coordinate authorized stabilization; use Debug for causal investigation.
- For `/security-review` or scoped vulnerability assessment, follow `architecture/security-review.md` as a security-focused Review. Validate realistic attack paths and keep production testing and secret exposure within project authorization.
