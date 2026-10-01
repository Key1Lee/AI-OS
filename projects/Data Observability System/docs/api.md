# Public contracts and consumer boundary

The stable Python import remains `data_system_map`; the distribution is
`data-observability-system`. `create_service(path, seed_demo=False)` constructs the
engine. Public methods are `systems`, `import_dbt`, `snapshot`, `graph`, `node`,
`relation`, `impact`, `changed_nodes`, `incidents`, `investigate`, `explain` and
`query`. Normalized schemas and provenance retain contract version `data-map-v1`.
The graph, adapter, metadata schema and traversal algorithms were moved unchanged.

`mount_map_routes(app, runtime)` mounts one canonical `/api/map` router:

- `GET /systems`, `POST /systems/import`
- `GET /systems/{id}/graph`, `/search`, `/explain`, `/incidents`, `/incidents/{node}`
- `GET /systems/{id}/nodes/{node}` and `/schema`, `/tests`, `/sql`, `/upstream`,
  `/downstream`, `/impact`, `/columns/{column}/lineage`
- `POST /systems/{id}/query`, `POST /debug/investigate`

Query operations retain direct/transitive dependencies, bounded paths, failed
paths, impact, changes and explicit unavailable column lineage. Imported SQL is
never executed. Node details exclude SQL text; the explicit SQL route serves it.

`MapContext` owns the engine reference and optional consumer hooks:
`view_options`, `action`, `ensure_import_allowed`, `require_explanation`,
`project_incident`. Generic options select a snapshot, diagnostics and an opaque
`audience` label. The engine contains no assessment rules or candidate policy.
Standalone diagnostic evidence is available by default. Toptal chooses visibility
from its current server-side session; query parameters cannot override it.

The trainer alone mounts `/api/map/investigations*`, controls grading, prohibits
imports during assessment and hides automatic cause designation and next steps.
Explicit inspection of a node's recorded evidence remains available, as before.
The generic app provides no alternate route on the trainer server.

Existing statuses, safe validation/errors, 8 MiB server upload bound, atomic
imports, 14-node display cap and graph query bounds are preserved. Shared HTTP
boundary installation authorizes mutations before reading a chunked body.
No SQL-analysis API is claimed because that feature does not yet exist.
