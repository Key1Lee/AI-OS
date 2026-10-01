# AI-OS Skills

## Architecture discovered and retained

Before this layer, AI-OS had a shared `py_dev` model router and runtime, global and provider TOML configuration, a minimal Toptal-Testing project override, and independent Toptal-Testing and Northstar applications. Qwen through loopback llama.cpp was the default shared runtime; optional OpenAI and Claude adapters were disabled without explicit flags and a cloud-call budget. There was no repository Skill root, Skill resolver, or source registry. Existing project applications remain independent and are not implicitly migrated.

## Boundary

```text
user request or $skill / /skill
  → canonical Skill resolver (`skills/catalog.toml` + `skills/<name>/SKILL.md`)
  → semantic task profile (`config/defaults.toml` or project override)
  → existing config hierarchy: global → provider → project → task → run
  → existing AIOSRuntime → ModelRouter → provider adapter
  → application-owned state, verification, and traces
```

Skills describe **what to do**. Task profiles describe **how**; the runtime selects the configured provider and translates reasoning/context policy. `py_dev.skills.SkillRunner` supplies Skill instructions as system instructions and calls the existing runtime. It does not grant tools. The `audit` path supplies deterministic checker evidence; `grill-me` checkpoints answers in application-owned state before the next model call. For local Qwen runs, a small lexical lookup can supply matching registered **route metadata** without reading source bodies; cloud runs do not receive those routes automatically. Skill descriptions are read from canonical `SKILL.md` frontmatter, while `catalog.toml` contains only activation patterns and task profile routes. Explicit `$name` and `/name` commands win over indirect matching. Ambiguous indirect matches fail and require an explicit command.

| Skill | Trigger and output | Task profile | Deterministic resource | Boundary |
|---|---|---|---|---|
| `onboard` | Start or refresh operating context; return confirmed changes and gaps | `skill_onboard` | Confirmed-context merge script | No credentials or unconfirmed durable facts |
| `grill-me` | Interview one question at a time; return next question or synthesis | `skill_grill_me` | Interview checkpoint store and script | Session can pause; model context is not the record |
| `link` | Register a discoverable source; return route and verification state | `skill_link` | Source registry and path verifier | No bulk ingestion or assumed external access |
| `audit` | Assess AI-OS architecture and conformance; return evidence-labelled findings and coverage limits | `skill_audit` | Bounded checker with stable finding IDs | System-level audit, not completed-change Review; read-only unless report saving is requested |
| `level-up` | Select one evidenced improvement; return proposal or authorized change | `skill_level_up` | None needed for the decision itself | No fabricated usage or automatic new Skill |
| `3d-brain` | Build an optional view of approved routes; return local HTML | `skill_3d_brain` | Metadata-only viewer generator | No source-body copy or Core dependency |

The default provider for every task profile is inherited `qwen_local`. `audit` uses high semantic reasoning but remains local by default. A project can set `[task_profiles.skill_audit] provider = "openai"` when its explicit provider enablement and budget policy permit that choice. Native Codex execution of `$audit` uses Codex's own agent; it does not imply an OpenAI API call through `py_dev`. Claude remains optional. The existing capability registry and live Qwen report describe locality, context, thinking controls, and configured cloud access; none confers filesystem permission.

| Provider | Skill routing role | Availability evidence | Cost and permission boundary |
|---|---|---|---|
| `qwen_local` | Default for normal, interview, classification, and first-pass work | GGUF, loopback health, loaded identity, context, and thinking are checked live | Local inference; no tool authority |
| `openai` | Optional configured engineering or independent review | Enable flags, model name, and budget make it eligible; connectivity requires an actual call | Cloud budget gates apply; no tool authority from model choice |
| `claude` | Optional alternate reviewer or engineer | Enable flags, model name, and budget make it eligible; connectivity requires an actual call | Not required for core operation; no tool authority from model choice |

`py_dev.capabilities.skill_capability_matrix` exposes this conservative view. Cloud eligibility is not proof of a successful remote call.

For example, `SkillRunner.run("$grill-me ...", project="Toptal-Testing", overrides={"reasoning": "none"})` resolves global Qwen → Qwen provider endpoint → Toptal project output preference → `skill_grill_me` medium/small → run reasoning `none`. The project does not copy global defaults. A normal unmatched task follows the same runtime with no Skill and defaults to Qwen.

## Canonical source and adapters

Author only in `skills/<name>/`. `scripts/sync_skills.py` generates `.agents/skills/` for Codex and `.claude/skills/` for Claude. The generated directories carry a hash manifest. Sync refuses to overwrite a modified mirror; `--check` fails on drift. No independent provider-specific instructions are maintained. A new Codex or Claude session may be needed for native Skill discovery to refresh. Qwen uses the canonical Skill catalog directly through `SkillRunner`; the model never searches the filesystem for Skills itself.

```sh
python3 scripts/sync_skills.py
python3 scripts/sync_skills.py --check
python3 -m py_dev skill list
python3 -m py_dev skill run '$grill-me about a plan' --reasoning none --max-output 128
python3 -m py_dev skill run '$audit the AI OS' --reasoning none --max-output 1024
```

`SkillRunner` is also callable from another application. Its `session_id`, `answer`, and `question` arguments support interview resume and checkpointing. Application integrations must own any authorized writes; the Qwen adapter remains a model interface and has no tool executor. For deterministic operations, use the scripts linked in each Skill. Global private state defaults to `~/.local/share/ai-os/state` or `AIOS_DATA_DIR`; project state stays under `projects/<name>/state/`. A source registry stores routes and evidence metadata, never a copy of the source. Audit reports are not saved automatically; `skills/audit/scripts/check.py --save` explicitly writes a dated local record.

The Qwen CLI conducts interviews and presents recommendations, but it does not automatically apply `onboard` or `link` writes from prose. Run their application-owned scripts after confirming the data, or integrate the corresponding Python store functions in a project application. This keeps model output separate from authorized persistence.

The optional 3D viewer requires explicit route IDs and produces a self-contained local HTML file. It reads registry metadata only. It is an exploration interface, not a persistent knowledge store.

## Evaluation and limits

`tests/test_skills.py` checks direct, indirect, incomplete, edge, and non-activation prompts for every Skill; instruction and profile loading; project and per-run routing; Qwen-default and optional cloud selection; permission invariance; context and inheritance; checkpoint persistence; confirmed-context merging; source validation; and broken audit fixtures. Per-Skill case files live in `skills/<name>/tests/cases.toml`; `evals/audit-cases.toml` adds architecture-audit and adjacent-workflow routing controls plus stipulated finding cases. The official quick validator checks each frontmatter package. `skills/audit/scripts/check.py --live` checks actual local runtime identity and health. The checker is bounded: it does not prove every project workflow, external connection, or permission path works. A short-output audit model run may be incomplete; allow sufficient output tokens or inspect the deterministic JSON directly.

The audit routing cases improved from 12/19 with the previous catalog to 19/19 with the revised patterns. In five stipulated-evidence local Qwen finding cases, a basic classification prompt scored 1/5 exact labels and the revised Audit instructions scored 4/5; one response used a noncanonical label for an instruction conflict. The local Skill runner produced a bounded checker report with sufficient output tokens, but its model has no repository tools and cannot complete a system-level architecture audit alone. These small trials do not establish cross-model reliability.

## Research and attribution

This design follows current [official OpenAI Skill guidance](https://developers.openai.com/plugins/build/skills) on focused workflows, concise descriptions, supporting resources, scripts only where useful, and representative tests, along with [OpenAI's recent advice](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) to keep descriptions and `AGENTS.md` lean and disclose detail progressively.

The six workflow names and useful lifecycle patterns were adapted from [Nate Herk's AIS-OS](https://github.com/nateherkai/AIS-OS) (inspected at commit `ce9cb93a1145da5daba84ea37208ec35fd03606e`). We retained focused onboarding, interviews with checkpoints, source routing, evidence-based audits, one-improvement planning, and optional visualization. We replaced Claude-first authoring and duplicated generated Skill copies with a model-independent canonical root and safe generated mirrors; we did not copy its full rubric, application template, automatic report persistence, or the trademarked Three Ms/Four Cs frameworks. Nate Herk retains attribution for those source concepts and names.
