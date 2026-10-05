# ADR-002: Consumer-owned adapter boundary

Status: accepted for Phase 1.

**Context.** Five independent projects already implement useful engine logic,
but use different languages, dependencies and bounded interfaces.

**Decision.** Keep all Lab translations and workers in this project. Invoke
native typed SDKs in existing sibling runtimes, and the TypeScript orchestrator
through its installed `tsx`. Configure paths, expose Lab protocols and fail
visibly if a required native runtime is unavailable. Preserve sibling sources,
operational databases and learner evidence.

**Alternatives.** Copy engine logic; modify every system into a common framework;
start five HTTP services; merge incompatible runtime dependencies.

**Tradeoffs.** Subprocess overhead is acceptable for a small local exercise.
File-level native APIs need explicit provenance and contract tests because their
release packaging is incomplete.

**Consequences.** The native orchestrator owns attempt decisions while the Lab
executes actual writes. Modeling and quality retain their evaluators; complete
key-group partitioning adapts their input limits. No mocked success replaces an
unavailable system, and infrastructure errors are separate from learner failures.
