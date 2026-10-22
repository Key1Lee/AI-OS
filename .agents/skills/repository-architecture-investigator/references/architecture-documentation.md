# Optional arc42 documentation

Read when arc42-inspired organization would clarify the reconstructed architecture or the user requests it. Use arc42 to communicate evidence, never to establish architectural truth. Keep the result in the conversation unless the user requests a saved report; repository documentation changes require an explicit request.

Select only sections that answer the scoped questions. Existing project documentation conventions take precedence over adding a parallel architecture document.

| Useful section | Evidence and limits to communicate |
| --- | --- |
| Introduction and Goals | What the repository implements, intended users, and explicitly stated goals. Distinguish documented purpose from implemented capability. |
| Architecture Constraints | Constraints established by build, interfaces, configuration, hardware, or project requirements; separate imposed constraints from inferred preferences. |
| Context and Scope | The investigated boundary and evidenced external interfaces. Mark inaccessible consumers or systems. |
| Building Block View | Responsibilities, interfaces, and dependencies established from source or declarative artifacts; directory names alone do not establish components. |
| Runtime View | Relevant source-derived possible sequences or identified observed runs, with their conditions and different evidence statuses. Omit unsupported execution paths. |
| Deployment View | Declared topology and environment conditions. Separate desired state, local setup, and observed deployment. |
| Architecture Decisions | Link explicit decisions and their documented rationale. Label inferred design choices and state when rationale is unknown. |
| Risks and Technical Debt | Evidence-backed limitations, assumptions, and failure boundaries. A hypothetical failure scenario is not an observed defect or confirmed debt. |

Retain source references and uncertainty next to significant conclusions. Do not turn missing evidence into a completed template section. Reuse an existing evidence ledger or diagram rather than repeating it under several headings.

When documenting a mismatch, state what documentation says, what the inspected implementation establishes, and which conditions or missing evidence could explain the difference. Do not invent historical reasons or rewrite the project's intent.

The [official arc42 overview](https://arc42.org/overview/) describes the full template. This skill uses a relevant subset; additional sections are optional when the question warrants them.
