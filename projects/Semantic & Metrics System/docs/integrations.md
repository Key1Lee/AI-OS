# Artifact integration contracts

These are implemented exports and input validation, not live sibling connections. No sibling package is imported, no sibling state is changed, and no warehouse/BI/provider account is called. Discovery evidence lives in [semantic-inventory.md](semantic-inventory.md).

| System | Implemented local interface | Producer/consumer ownership | Current proof and limitation |
|---|---|---|---|
| Modeling | `modeled-semantic-snapshot-v1`, `adapters.artifacts.modeled_input`, `sem export modeling` | Modeling supplies one Order row and one refund aggregate per Order plus unique Customer/Product dimensions; Semantics validates needed grain and consumes rows | Bundled already-modeled fixture executes; live Modeling SDK export mapping remains uninstalled |
| Quality | `semantic-check-requirements-v1`, `sem export quality` | Semantics names required identity/cardinality assumptions; Quality owns check execution and native `quality-event-v1` / `quality-gate-v1` truth | Requirements export executes; no native Quality check or quality PASS is fabricated by this adapter |
| Observability | `sem export observability` emits a `data-map-v1` artifact inside `semantic-integration-v1` | Semantics supplies declared metric/version/upstream/consumer metadata; Observability owns recorded freshness, dependency failures and incidents | Graph export has coherent IDs and edges with UNKNOWN status and `sample=true`; no live map ingest is claimed |
| AE Lab | `semantic-incident-reference-v1`, `sem export ae-lab` | AE retains orchestration, run state and assessment; Semantics exposes scenario reference | Artifact identifies SEM-REVENUE-001 and its entry point; no installed native AE semantic adapter |
| FDE Lab | `semantic-discovery-handoff-v1`, `sem export fde-lab` | FDE discovers decision/owner/constraints; Semantics formalizes explicit meaning | Export includes an authored contract and required discovery fields. FDE Northstar FIN-NET-1 remains UTC completed net; it is not mapped to Chicago fulfillment by name |
| Orchestration | Reference only to `orchestration-event-v1` inspected schema | Orchestration owns when/how refresh runs | No scheduler or task runner added |
| AI-OS | Shared engineering boundary and guidance only | AI-OS owns provider/runtime routing; this project owns business meaning | No provider client, router override or prompt-defined metric |
| Toptal Testing | No state integration | Toptal owns independent assessment and mastery | Local semantic practice cannot update its scores or certify learner understanding |

An integration export includes metric ID/version, definition and artifact fingerprints, `scope=synthetic_scenario`, `connection=artifact_contract` and `live_connection=false`. Producers must retain their own contract versions and provenance when live adapters are later implemented.

Example governed AI tool request:

```json
{"contract_version":"semantic-query-v1","metric_id":"net_revenue","version":"1.0.0","consumer":"ai","start":"2026-09-30","end":"2026-10-02","dimensions":[]}
```

The application must select the explicitly approved contract for its customer. The result gives deterministic meaning and provenance for the model to explain. The model cannot add a formula, change the timezone or invent ownership through this interface.
