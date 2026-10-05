# Original commerce demonstration

These checked-in artifacts are **synthetic dbt-shaped exports**, not artifacts
from a dbt command or a production commerce account. Shopify is an authored source
label. The trusted generator `python -m data_system_map.demo.generate` executes original
in-memory DuckDB transformations and checks, then emits deterministic metadata.

Three orders have expected revenue 160. Five order items cause the deliberately
unaggregated intermediate LEFT JOIN to produce duplicate order groups (2 groups)
and revenue 270. The fact uniqueness check fails; the staging check passes. These
measurements are genuine generator output over synthetic data. Producer metadata,
artifact hashes and pointers trace the reported evidence. The fixed timestamp is
2026-10-02T00:00:00Z for reproducibility, not a live runtime timestamp.

Run `make check-map-demo` to regenerate in memory and compare all four JSON files.
Running `.venv/bin/python -m data_system_map.demo.generate` explicitly rewrites
the fixture exports. Neither command creates learner attempts or mastery evidence.

The scenario private rubric lives in the trainer integration and is absent from
the public graph. Learning can reveal evidence-supported suspicion; assessment
requires explicit inspection. A local owner can read source files, so this is a
training policy boundary rather than a secrecy mechanism against the machine owner.
