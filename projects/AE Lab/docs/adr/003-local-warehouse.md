# ADR-003: Isolated SQLite warehouse

Status: accepted for Phase 1.

**Context.** A partial write must survive failure and be inspectable. Native
modeling already supplies DuckDB SQL execution; the Lab still needs durable
loader state, safe repair and resumable evidence.

**Decision.** Create a per-run SQLite warehouse with `orders_raw` and `fct_orders`
under the selected Lab state directory. Store money as integer cents. Commit
the deliberately partial load, then execute the native retry trace. Repair
historical duplicates atomically, install an order-key unique index and upsert.

**Alternatives.** A Python list; a shared sibling warehouse; PostgreSQL/Docker;
a second SQL transformation engine implemented in the Lab.

**Tradeoffs.** SQLite provides real transaction and constraint behavior without
a service. It does not model distributed writers or warehouse-scale concurrency.
Native modeling continues to own candidate transformation and assertions.

**Consequences.** Runs are isolated and reproducible. Complete recovered rows
and monetary values can be compared to independent fixture references. This
repair policy handles the frozen identical-duplicate scenario; competing source
versions and last-writer ordering require a future explicit contract.
