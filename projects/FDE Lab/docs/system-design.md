# Design canvas

```text
Actor → authenticated boundary → application → state / external dependency
            │                      │                 │
            └────────── telemetry and ownership ─────┘
```

Draw your own actors, components, contracts, data/control flows, state, failure boundaries, security boundaries, and telemetry. Label unknowns rather than hiding them in a box.

For one choice explain: choice → reason → alternative → tradeoff → failure mode → reconsideration trigger. Trace one request and one recovery path. Ask why a simpler workflow is inadequate before introducing a new service.
