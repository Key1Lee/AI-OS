---
name: grill-me
description: Conduct a one-question-at-a-time discovery interview when the user wants to unpack a plan, idea, decision, or operating context.
---

# Grill me

Input: a topic or decision to explore. Use relevant existing project context before asking. If the topic is missing, ask for it. Ask one useful question at a time, adapting to the prior answer; do not repeat answered questions or invent personal facts.

The application owns the checkpoint. Save each answer with its question, evidence status (`unclassified`, `confirmed`, `hypothesis`, or `idea`), and open flags before asking the next question. Default to `unclassified` until the user or evidence supports a stronger label. The [checkpoint procedure](references/checkpoints.md) applies when starting, resuming, or saving an interview. On pause, report the session ID and open question. Promote only user-confirmed durable facts to canonical context, and only when asked to update that context.

Output: the next single question, or a concise synthesis with confirmed facts, hypotheses, unresolved flags, and resume location. Stop immediately on an explicit stop. If checkpointing fails, preserve the answer in the conversation and do not continue collecting answers as though it was saved.
