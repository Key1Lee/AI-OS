# Systems map

AI-OS is the shared engineering workspace. Each populated directory under
`projects/` remains an independent project. This map describes the current
files; it does not imply a production pipeline or a running service.

## Who owns what

| System | Purpose / owns | Does not own |
| --- | --- | --- |
| [AI-OS](systems-registry/registry/ai-os.yaml) | Shared guidance, Skills, configuration, model routing, and this map | Project business logic, credentials, databases, and scheduling |
| [Data Modeling](systems-registry/registry/data-modeling.yaml) | Learn grain, staging, joins, facts, and model invariants | Scheduling, monitoring, learner assessment, shared metric governance |
| [Data Orchestration](systems-registry/registry/data-orchestration.yaml) | Simulate task ordering, retries, partitions, and backfills | SQL transformations, production scheduling, and incidents |
| [Data Quality](systems-registry/registry/data-quality.yaml) | Data contracts, rule checks, compatibility, and gate evidence | Transformations, scheduling, monitoring, and learner scoring |
| [Data Observability](systems-registry/registry/data-observability.yaml) | Metadata graph, lineage, incidents, impact, shared API and map UI | Learner scoring, disclosure, and warehouse execution |
| [Semantic & Metrics](systems-registry/registry/semantic-metrics.yaml) | Business meaning, governed metrics, bounded snapshot evaluation | Ingestion, scheduling, general quality, and monitoring |
| [Analytics Engineering Lab](systems-registry/registry/analytics-engineering-lab.yaml) | Guided retry-safety scenario, local warehouse, adapters, and evidence | Sibling engine logic, canonical mastery, and production connectors |
| [Forward Deployment Engineering Lab](systems-registry/registry/forward-deployment-engineering-lab.yaml) | Synthetic customer discovery, SQL practice, and learner progress | Real deployment, production incidents, and sibling engine state |
| [Toptal Testing](systems-registry/registry/toptal-testing.yaml) | SQL practice, assessment, adaptive training, mastery, learner map extensions | Generic observability engine and official hiring acceptance |
| [n8n / Northstar](systems-registry/registry/n8n-system.yaml) | Existing local n8n runner and deterministic lead-intake workflow | The orchestration learning simulator and other projects' credentials |

## Where they live and how they connect

Locations are relative to `/Users/key/_AI-OS`. Dependency arrows below mean
implemented sibling code/runtime use. Exported artifact compatibility is
listed separately. `None proven` means no such registered dependency was found;
it does not establish that every possible relationship has been investigated.

| System | Current directory | Uses registered systems | Used by |
| --- | --- | --- | --- |
| AI-OS | `.` | None proven | Toptal provider consumers; shared guidance also applies |
| Modeling | `projects/Data Modeling System/` | None proven | AE Lab |
| Orchestration | `projects/Data Orchestration System/` | None proven | AE Lab |
| Quality | `projects/data-quality-contracts-system/` | None proven | AE Lab |
| Observability | `projects/Data Observability System/` | None proven | AE Lab, Toptal |
| Semantic & Metrics | `projects/Semantic & Metrics System/` | None proven | UNKNOWN |
| AE Lab | `projects/AE Lab/` | Modeling, Orchestration, Quality, Observability, Toptal | UNKNOWN |
| FDE Lab | `projects/FDE Lab/` | References only; runtime connections UNKNOWN | UNKNOWN |
| Toptal | `projects/Toptal-Testing System/` | Observability package/UI; AI-OS provider transport | AE Lab |
| n8n / Northstar | `projects/n8n System/` | None proven; external service readiness UNKNOWN | UNKNOWN |

```text
Shared engineering guidance: AI-OS

Implemented sibling code/runtime use (consumer -> provider):
AE Lab -> Modeling, Orchestration, Quality, Observability, Toptal
Toptal -> Observability
Toptal provider consumers -> AI-OS

Other independent projects in this map:
Semantic & Metrics    FDE Lab    n8n / Northstar
```

AE Lab owns its subprocess adapters. Toptal imports Observability's package
and UI source. Neither relationship establishes a deployed network service.
The existing source evidence is in AE Lab's `lab/adapters/bridge.py` and
`lab/adapters/workers/`, and Toptal's `apps/api/data_map.py` and
`apps/web/vite.config.ts`.

Orchestration implements an optional serialized Modeling adapter. Quality
implements Modeling input conversion and Observability record output. These
artifact interfaces do not establish an operating Modeling → Quality →
Observability pipeline. See each registry entry's interface and contract paths.
FDE's existing `integrations/registry.json` describes references and future
adapters; it remains project-owned.

## Known limits

- `projects/Data Quality System/` is an empty folder. The quality implementation
  is mapped to its existing `data-quality-contracts-system/` directory.
- Semantic core, CLI, tests, schemas, and artifact adapters now exist. Their
  declared checks are recorded; application execution and installed sibling
  connections remain unverified by this setup.
- Lifecycle status and executable health checks remain UNKNOWN for all entries.
  Test commands describe existing project instructions; this registry setup did
  not execute the projects' suites or prove application health.
- The old `Northstar` and `Toptal-Testing` paths appear in some existing shared
  documents/Git history. This map uses the directories that exist now.
- `projects/Sandbox/` is empty and has no confirmed system purpose. Other sibling
  folders outside AI-OS are outside this initial registry's scope.

For a task, find the owner here, read its one YAML entry and local `AGENTS.md`,
then inspect the relevant contract and source files. Cross a system boundary
only when the change requires it. See [architecture](ARCHITECTURE.md) and the
[registry conventions and validator](systems-registry/README.md).
