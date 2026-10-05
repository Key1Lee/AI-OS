# Evidence before release

```text
Task → dataset → expected behavior → evaluator → metric
 → customer-approved threshold → regression → release decision
```

Separate model behavior, whole-system behavior, and business outcome. A local SQL result, an assistant response, and a morning-review time study answer different questions. Name which one your experiment tests.

Use `fde evaluate` to defend the release evidence and remaining unknowns. Do not substitute a confident answer or green infrastructure status for correctness.
