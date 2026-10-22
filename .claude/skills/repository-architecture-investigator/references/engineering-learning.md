# Engineering learning and active recall

Read for a guided architecture-learning session or when deeper recall practice helps the engineer use the reconstructed model. Base questions and explanations on inspected artifacts. Do not add an assessment framework or learner records to the repository.

Build a short prioritized reading path. Start with the artifact that establishes purpose, boundary, or public contract; continue through the most informative wiring and transformation/state logic; then inspect a relevant test, configuration, or failure boundary. Use functions and precise source references where available. Adapt the path for declarative, infrastructure, embedded, and library repositories instead of assuming an application entry point. Explain what each reading resolves.

Move from system purpose and boundaries to relationships, then to implementation detail. Choose the questions that reveal the most consequential gaps in the engineer's model:

| Reasoning to practice | Adapt to actual repository evidence |
| --- | --- |
| Responsibility | Why does this identified component exist, and which inspected contract supports that explanation? Separate observed responsibility from unknown historical rationale. |
| Prediction | Under a stated input or configuration, which established branch runs and what changes? |
| Data and state | Follow a value through actual transformations or state transitions; identify where its representation or owner changes. |
| Dependency and invariants | Which evidenced relationship or precondition must hold for the scoped behavior? |
| Failure investigation | If an established dependency became unavailable, what does the source imply, and what observation would distinguish plausible outcomes? Label the scenario hypothetical. |
| Evidence discipline | Which claim remains an inference, and what accessible evidence could confirm or falsify it? |

Prefer explanation and prediction over recalling filenames. A repository without runtime access can still support questions about static relationships and the evidence needed to establish behavior. Do not supply hidden implementation details or invent an answer when the evidence is insufficient.

For an interactive exercise, ask the engineer to reconstruct a supported flow or relationship without reopening the code, then compare their explanation with the evidence. A missing link is a prompt for a focused investigation, not proof of incompetence. Honor hint-only, answer-withheld, and learner-led requests; do not disclose the answer key prematurely. When a flow cannot be established, practice explaining that limit and selecting the next discriminating check instead.
