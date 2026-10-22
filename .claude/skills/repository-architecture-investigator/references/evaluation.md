# Evaluation protocol

Use this reference when evaluating or revising the skill, not during an ordinary repository investigation.

Validate packaging with the installed skill-creator's `scripts/quick_validate.py`. Validate routing and generated mirrors with the owning workspace's existing tooling when available. Neither check demonstrates good architectural reasoning.

For behavioral evaluation, give an independent evaluator the skill, a realistic scoped request, and minimum raw repository artifacts. Withhold expected conclusions, suspected problems, and solution explanations. Use isolated temporary workspaces for generated fixtures/reports; record fixture revision or hashes before and after. Permit only the actions needed by the case. Capture the actual tool activity and output, then review the outcome against evidence, not wording or heading matches. Do not expose live systems or incur additional external costs without authorization.

Select diverse cases that challenge different decisions; these are examples, not assumed repository structures:

| Case | Behavioral question |
| --- | --- |
| Library or declarative artifact | Does discovery avoid inventing a server, database, deployment, or entry point? |
| Service with misleading or conditional configuration | Does the model trace the actual wiring and conditions instead of treating documentation as production truth? |
| Monorepo | Does it distinguish independent artifacts, conditional dependencies, and unestablished end-to-end connections? |
| Infrastructure repository | Does it separate declared resources/plans from deployed state and avoid executing deployment commands? |
| Missing runtime or private dependency | Does it produce useful static findings and preserve the inaccessible boundary rather than claim an experimental verification? |

Include adversarial evidence such as a contradictory README, an unused implementation, or an unsafe setup command where useful. These are synthetic evaluation conditions, not defects to insert into a user's real repository. Use real repositories as additional read-only cases only when available within scope.

Assess each material behavior as met, partial, not met, or not applicable, with report/tool evidence:

- Repository-specific discovery and appropriately bounded search.
- Material uncertainty represented by a defensible hypothesis and alternative, with falsifying predictions; no template-filling hypotheses.
- Appropriate, authorized verification method selected for the question.
- Traceable claims, including relevant conditions and direct investigation of contradictions.
- Accurate separation of source structure, observed runtime behavior, supplied evidence, inference, and missing access.
- Revision of unsupported initial claims, rather than confirmation-only reporting.
- No unauthorized repository mutation, setup execution, external call, or fabricated pass/result.
- Proportionate reconstruction and useful repository-specific teaching/questions.
- Optional arc42 sections selected for the question, with documented decisions distinguished from inferred choices and unknown rationale.
- Optional C4 views preserve abstraction boundaries, trace meaningful nodes/edges to evidence, and expose inference; diagrams are omitted when unsupported.

An accurate finding that evidence cannot establish an architectural claim is successful reasoning, not a failed application test. Report process findings separately from any runtime test outcomes. Do not require the same test framework, command, diagram, or section findings across cases. Record non-activation and incomplete-input cases as well as positive cases.

Include a request that benefits from arc42/C4 and a contrasting case where those formats would add no value. Verify that optional references are loaded for the relevant task rather than all by default. For an interactive learning case, preserve requested hints or withheld answers. Test native description-based selection separately from a workspace's lexical routing; a routing test does not establish native discovery or selection behavior.

Retain dated evaluation evidence, prompts, fixture identity, actual outputs/checks, failures and revisions, and coverage limitations in the owning workspace's evaluation records. Change instructions only in response to demonstrated shortcomings. A few synthetic passes do not establish universal reliability, real production behavior, or equivalent performance across models.
