# FDE mental model

```text
WHAT → WHY → WHERE → HOW → WHAT CAN BREAK
 → HOW DO WE KNOW → HOW DO WE FIX IT → WHY THIS DESIGN

Business workflow → system boundary → runtime behavior → code
        ↑                                           ↓
        └───────── measured customer value ─────────┘
```

Choose one observation. Trace it. Identify its owner and contract. Distinguish facts, assumptions, and unknowns. Design the smallest experiment that could disprove your explanation. Scale architecture only after requirements justify it.

Recall: What problem would remain even if the visible component worked perfectly?
