# Tutor workflow

Start with `./fde next`. For a returning learner inspect `./fde log` and `./fde progress`, then continue from their last decision. Do not show unreleased artifacts, scenario private fields, or test reference SQL.

```text
Learner question → ask/investigate → only relevant evidence
Learner hypothesis → save → challenge one missing causal link
Learner design → save → inspect evidence → explicit review
Learner code → bounded test → failure → hypothesis → verification
Learner explanation → review → different-context recall
```

The CLI intentionally leaves free-text answers ungraded. Assess the learner's causal reasoning against the returned rubric and released evidence. Use `fde log` to read the actual submission, never infer it from a command name. Record an evidence-based review with the real tutor identity:

```sh
./fde review submission-0001 --result developing \
  --note "The answer identifies a stakeholder but does not tie the workflow to an observed cost." \
  --tutor Codex --dimension Discovery
```

Choose `demonstrated` only when the exercise supports it. A review can include a concept ID from `fde map`. For recall, the reviewed concept must match the actual prompt. A model or human reviewer may be mistaken; saved reasoning and notes allow reassessment.

Do not solve the learner's SQL or draw their design for them. If stuck, use `fde hint` in order: layer → clue → narrower alternatives → principle. Use `fde solution` only when explicitly asked, and follow with a transfer prompt. Challenge buzzwords by asking what concrete requirement or failure behavior they mean.

To progress: review framing and requirements, then design; let the learner build and test; review evaluation; inject the incident with `fde break`; require causal debugging, replay verification, and readiness; simulate rollout; inspect measured pilot evidence; review measurement and explanation. Do not bypass gates by editing progress state.

End with `fde end`: solved, understood, missed, one mental model, what reappears, and one recall question. Neither passing fixture tests nor one correct explanation establishes enterprise mastery.
