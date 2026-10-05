# Approved first-slice acceptance

Source: the user's pasted request, particularly FIRST VERTICAL SLICE, EXACTLY ONE
HELPER AGENT, the completion concepts, and the four system boundaries.

| Criterion | Required evidence |
| --- | --- |
| Deterministic, vendor-neutral DAG | Stable order; unknown/duplicate dependencies and cycles rejected; identical explicit inputs yield identical traces. |
| Dependency/state correctness | Diamond join waits for both successes; terminal failure blocks descendants but independent work succeeds; WAITING/READY/RUNNING/SUCCESS/FAILED/RETRYING/BLOCKED/SKIPPED only. |
| Simulator | Authored duration/failure outcomes; multiple workers and pool limits; timeout failure; one-success/all-done behavior; no real time or AI in truth engine. |
| Retry | Transient failure releases capacity, waits exact delay, increments attempts, then succeeds/exhausts; deterministic bad SQL is not repaired by retries. |
| Schedule/asset trigger | Daily 06:00 Asia/Seoul gate is independent of dependencies; invalid/unrelated asset events rejected; explicit asset availability can start the same workflow. |
| Reruns/idempotency | Same 100-row payload gives 100→100 for replacement and 100→200 for append; reruns preserve output state; unknown safety is shown as unknown. |
| Backfills/partitions | Sep 27–29 range; one partition can fail independently; successful partitions skipped or explicitly replaced; today's execution timestamps; bounded range; global workers and partition concurrency. |
| Critical path/timeline | Longest duration-weighted dependency chain computed deterministically; shorter parallel branch does not change it; actual attempt bars include retries and contention. |
| Beginner UX | Stage overview first; task reveal, task details, grounded “why” and blocked/failed distinction; eight questions visible; pipeline/assets/timeline and backfill interaction; usable narrow layout. |
| Integration boundaries | Runtime-valid event/scenario schema exports; Modeling envelope dependency adapter preserving metadata; no sibling imports, SQL business logic, scoring, incidents, or real vendor integration. |
| Automated checks | Engine/contract regressions and build pass; production browser learning journey, export/rerun/backfill/mobile pass. |
| Independent verification | Exactly one helper agent inspects/tests independently; evidence per criterion; no blocking correctness errors; PASS after fixes. |
