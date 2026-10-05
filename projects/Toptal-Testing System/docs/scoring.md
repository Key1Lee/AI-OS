# Scoring and mastery

Policy version `ae-v1`. SQL outcome is Correct when every category passes,
Partial when some pass, Incorrect when none pass. Syntax, resource and policy
errors are visible failures; infrastructure failures never count as learner
failure. Deterministic evidence cannot be overridden by an LLM.

If a query produces no usable result on any case (syntax, runtime, policy,
timeout or output-limit errors), only SQL execution receives gap evidence.
Joins, grain, NULL reasoning and other unobserved concepts keep their prior
state. Successful execution with wrong results can test those actual contracts.

Independent evidence requires all categories passing, no hints or solution
exposure, no prior submitted failure/exposure for this exercise, and no prior
successful credit for this exercise. Running the visible fixture is allowed.
Self-reported external assistance also disqualifies independent credit.
An attempt demonstrates SQL result correctness only; explanation quality is
unassessed without a reasoning evaluator.

0: no submitted evidence. 1: unsuccessful evidence without success.
2: assisted/revised success, or one independent success.
3: at least two independent successes across distinct exercise families.
4: at least four independent successes across at least three families, including
two L4+ exercises and a later cold retest, with no unresolved mistakes.
5: at least six independent successes across four families, including two L5+
exercises and two later cold retests, with no unresolved mistakes.
Cold retests require a different exercise and at least seven days since the
previous successful evidence. A fresh failure reopens a gap and caps the level
at Developing until verified transfer resolves it. There is no count-only
aggregate Senior readiness score.

Review intervals: failure 1 day; assisted success 3; independent success 7;
cold transfer 14; established senior evidence 30. Repeated failures shorten to
12 hours. These are persisted due dates, not background notifications.
