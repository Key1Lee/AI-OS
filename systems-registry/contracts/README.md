# Cross-system contracts

This folder will hold explicit cross-system interface definitions when they
are needed. No new schemas are introduced by the starter registry.

Existing contracts stay in their owning projects. Each registry YAML's
`contracts` list points to the original source. Current examples include:

- Modeling's `data_modeling_lab/contracts.py` and `docs/contracts.json`.
- Orchestration's `contracts/execution-event.schema.json` and `scenario.schema.json`.
- Quality's `quality_system/contracts.py` and `contracts/openapi.json`.
- Observability's core/API contract source files.
- Semantic's contract validation in `semantic/core.py`.
- AE/FDE Lab contract modules and Toptal's schema/assessment modules.

Use the exact workspace-relative paths in `../registry/`, not these abbreviated
examples, to open a file. A producer schema or adapter alone does not prove that
a consumer is connected or compatible. Record producer, consumer, payload,
version, failure behavior, and compatibility evidence before adding a new
cross-system contract. Keep project-specific contracts in their project.

The n8n/Northstar documentation references a contracts directory that was
absent at inspection; its registry does not invent or copy those schemas.
