# Deterministic adaptive engine

Candidates come from the current bank and prerequisites. Readiness begins at L3
for a diagnostic, decreases after failures and increases only after multiple
independent successes at the current level. User-selected practice can override
readiness; the recommendation itself explains eligibility.

Configurable factors in `curriculum/selection.yaml`: weakness, overdue review,
importance, difficulty match, untested coverage, unresolved mistake relevance,
transfer to another family, recent repetition and overpractice. Each recommendation
stores and displays the factor breakdown, not just a numerical rank.

Failures prioritize a materially different exercise testing the same competency.
Already credited exercises incur a repetition penalty and cannot generate new
independent mastery credit. If all content is exhausted, the UI explains the
coverage limit; repeated practice remains available. Selection is stable under
ties (exercise ID), deterministic under an injected clock, and never an LLM guess.

