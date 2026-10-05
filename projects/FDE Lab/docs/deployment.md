# Progressive delivery

```text
Local → dev → staging → internal → limited pilot → expanded rollout
                             ↑              │
                             └── rollback ──┘
```

Define entry evidence, owner, observation window, stop signal, rollback action, and recovery evidence before expanding access. `fde deploy` simulates one bounded pilot after readiness and replay checks. It validates the tested artifact again; it does not deploy any real endpoint.
