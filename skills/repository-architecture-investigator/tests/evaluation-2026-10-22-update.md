# Follow-up evaluation: 2026-10-22

## Scope and final artifact

Updated the existing investigator to integrate the user's expanded specification. The canonical source remains `skills/repository-architecture-investigator/`; existing UI metadata, routing/profile behavior, learning limits, evidence statuses, and the original evaluation record are preserved. The explicit scientific loop now follows OBSERVE → HYPOTHESIZE → PREDICT → INVESTIGATE → CHALLENGE → REVISE → RECONSTRUCT. Learning remains part of the output, with deeper guidance loaded only when relevant.

Final `SKILL.md` SHA-256: `f1f43b666045cf19b15af93f16faba94baf93125473d8848a219a9d9e926ce06`. The archive's `verification.json` identifies every evaluated instruction/reference file, including the visualization reference refined during evaluation.

Current pasted request SHA-256: `163062e7a82c212e930a099354ab3eb1888bea89d69b38066351247880ed7bc0`.

Files added: `references/architecture-documentation.md`, `references/architecture-visualization.md`, `references/engineering-learning.md`, and this record. Files updated: `SKILL.md`, `references/evaluation.md`, the investigator's two lexical routing patterns in `skills/catalog.toml` to include `verify`, and the existing `architecture/skills.md` description/installation/evaluation notes. The existing sync script regenerated Codex/Claude mirrors and their manifests. No runtime helper or dependency was needed; the existing skill was not reinitialized.

## User-level installation and discovery

Created these previously absent links without replacing an installation:

```text
/Users/key/.codex/skills/repository-architecture-investigator
  → /Users/key/_AI-OS/skills/repository-architecture-investigator
/Users/key/.agents/skills/repository-architecture-investigator
  → /Users/key/.codex/skills/repository-architecture-investigator
```

The requested installation path and the current [OpenAI user-discovery convention](https://learn.chatgpt.com/docs/build-skills) therefore share one canonical source. Installed `codex-cli 0.162.0-alpha.17.2` was queried through its local app-server `skills/list` protocol, using an isolated working directory outside AI-OS and `forceReload: true`. It returned one matching enabled skill with `scope: user`, the expected metadata, and no matching skill errors. No model turn was started for this discovery check. This demonstrates native discovery, not implicit model selection or a refreshed desktop picker.

## Mechanical checks actually executed

| Check | Observed result |
| --- | --- |
| Installed skill-creator `scripts/quick_validate.py`, canonical and user installation paths | Exit 0, `Skill is valid!` |
| `python3 scripts/sync_skills.py`, then `--check` | Exit 0; generated mirrors match canonical files |
| Final `python3 -m unittest discover -s tests -q` | Exit 0; 119 tests passed in 4.712 seconds |
| Local `SkillCatalog` smoke requests | Five positive verbs—understand, investigate, map, explain, verify—resolved to this skill; four unrelated coding/review/testing controls resolved to native handling |
| Relative skill-reference targets | All resolved |
| `git diff --check` | Exit 0; no whitespace errors |
| Parent fixture integrity checks | All 22 non-Git files across three fixtures retained identical hashes/revisions; Git status including ignored/untracked files was clean |
| Report citation bounds and reference definitions | 59 file/line references resolved to existing fixture files and valid line numbers; Markdown reference definitions resolved |

The first unit run was started before generated mirrors were synchronized and failed two mirror-consistency checks. After synchronization, all 119 tests passed. A later full run after the focused visualization clarification also passed, as recorded above. These are AI-OS integration/packaging checks, not standardized tests imposed on investigated repositories.

## Independent behavioral evaluation

Two evaluators with fresh chat contexts performed three realistic investigations. They received the skill, raw synthetic repositories, scoped requests, and access rules; no expected architectural conclusions or prior findings were supplied. A third fresh-context evaluator repeated the service request after one focused instruction refinement. The parent reviewed the actual reports/activity logs against source, rather than grading wording or headings.

| Fixture/request | Observed outcome |
| --- | --- |
| Small library, reading path and hint-only exercise | Distinguished the README's caller-order claim from sorting/merge behavior; predicted a falsifier before inspecting implementation; treated tests as unexecuted intent; provided a reading path and withheld the exercise answer. No arc42/C4 template was imposed. |
| Infrastructure, source access only | Reconstructed false-default conditional resource creation and nullable output; separated example inputs and documented deployment from observed state. Did not infer an unencrypted resource from missing encryption configuration. Omitted an unhelpful diagram with an explanation. |
| Service, selected arc42/C4 views and data flow | Traced per-callback memory-queue construction, conditional SDK publishing, and an independent stdin/stdout worker. Challenged the claimed durable pipeline and deployment wiring; retained unavailable SDK/production facts as unknown. Selected arc42 views and useful learning questions. The initial C4-style view grouped executables by source scope, earning a **partial** result for strict C4 system-boundary semantics. |
| Fresh focused service rerun | After the visualization reference clarified that repository scope does not establish one C4 software system, the evaluator explicitly chose an executable/dependency map. It preserved evidence-backed flow, conditional storage, unknowns, predictions, and learning support. This met the scoped boundary-selection criterion; it did not demonstrate a rendered or complete C4 model. |

The only payload change between initial evaluation and the focused rerun was the boundary-semantics paragraph in `references/architecture-visualization.md`. Initial and final bundles, both service reports, the contrasting reports, and review notes are retained separately. Optional references were selected for the requests: the service evaluations read documentation/visualization/learning guidance; the contrast evaluator read learning guidance without loading every optional reference.

All target investigations were static only. Activity logs record no application/test/setup execution, dependency installation, Terraform/cloud action, image build, or external service call. Parent integrity checks independently establish unchanged final fixture contents and Git trees; they do not prove absence of every possible transient action.

## Retained evidence and limitations

Durable archive: `/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/`.

- [Verification and artifact hashes](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/verification.json).
- [Native discovery result](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/native-discovery.json).
- [Mechanical check results](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/mechanical-checks.json) and [final unit output](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/final-unit-tests.log).
- [Initial qualitative review](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/initial-review.json) and [focused follow-up review](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-hvvd-vur/focused-review.json).
- `evaluation-requests.json`, `fixtures/`, `reports/`, `evaluated-initial-skill/`, and `evaluated-final-skill/` retain the requests, raw inputs, outputs/activity logs, and evaluated resources outside the working tree and generated skill mirrors.

Raw report source citations retain their original temporary prefix `/var/folders/cl/91y0ht7x1kz__0vw0psz8b2h0000gn/T/repository-architecture-update-hvvd_vur/`; the archive preserves the same fixture-relative paths, contents, and Git revisions.

These are three very small synthetic repositories and one focused rerun across three evaluator sessions, not a statistical benchmark or cross-model trial. New evaluation did not execute target runtime paths, render Mermaid, validate a complete C4 model, exercise large-repository scaling, or inspect production systems. Native implicit selection and picker refresh were not tested. Installation links require the canonical AI-OS path to remain available. The [original evaluation](evaluation-2026-10-22.md) remains unchanged and is separate evidence; neither record establishes universal reliability.

Invocation example:

```text
Use $repository-architecture-investigator to investigate /path/to/repository, trace a supported data flow, and explain the evidence and unknowns. Include arc42 or C4 only where useful.
```
