# Readiness questions

```text
Working prototype → explicit contract → measured behavior → bounded pilot
```

Who can request each action? Where are credentials stored? What is the time/cost limit? What fails safely? Which log, metric, trace, lineage, or quality signal detects it? Who owns support and rollback? What proves recovery?

Record these answers in `fde harden` using customer evidence. Security and reliability belong in the design and experiment, then receive deeper checks before rollout. A passing local fixture proves only its covered behavior.
