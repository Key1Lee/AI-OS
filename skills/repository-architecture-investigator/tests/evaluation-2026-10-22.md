# Evaluation record: 2026-10-22

## Evaluated artifact and scope

Instruction SHA-256: `6cbbb012e771d00eec18cd0856c23ba78af357da1617e866393a5f7366393fe8`.

Created from the user's supplied “Create a Universal Repository Architecture Investigation Skill” specification, SHA-256 `bc13ecbcbcceed273ff23e02e29715403d9284ca23eb5bdf481f6989a4a2f4ae`. The seven phases and evidence distinctions implement that request. Packaging and representative evaluation follow the installed skill-creator and the official [skill authoring](https://developers.openai.com/plugins/build/skills) and [skill evaluation](https://developers.openai.com/blog/eval-skills) guidance.

Canonical instructions, UI metadata and a maintenance-only evaluation reference are installed under `skills/repository-architecture-investigator/`. The AI-OS catalog uses an inherited-provider high/standard semantic profile; no provider permission or default was changed. Existing sync tooling generated the Codex and Claude mirrors.

## Mechanical checks actually executed

| Command, from AI-OS root | Result |
| --- | --- |
| `systems-registry/.venv/bin/python /Users/key/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/repository-architecture-investigator` | Exit 0, skill valid |
| `python3 scripts/sync_skills.py` | Exit 0, mirrors synchronized |
| `python3 scripts/sync_skills.py --check` | Exit 0, mirrors match canonical |
| `python3 -m unittest tests.test_skills.SkillCatalogTests -q` | Exit 0, 7 tests passed |
| `python3 -m unittest discover -s tests -q` | Exit 0, 119 tests passed in 4.776 seconds; includes the catalog tests above |
| `python3 -m py_dev skill list` | Exit 0, new skill listed |

Routing cases cover explicit, indirect, incomplete, edge and non-activation requests. These validate selection in the local catalog, not the quality of an architectural answer or the behavior of an incomplete native-agent conversation.

## Independent forward evaluation

One evaluator with no inherited chat history used the skill on five synthetic Git repositories. It received a realistic architecture-investigation request, raw artifacts, and per-repository access rules; no expected architectural answer or prior conclusion was supplied. It produced five investigation reports and an activity log. The parent inspected those actual outputs against the artifacts and the evaluation protocol.

| Fixture | Observed investigation behavior | Reviewer result |
| --- | --- | --- |
| Library | Established the public parsing API; challenged the README's production-server claim using packaging/source; inspected and then ran the permitted existing tests | Met within case; 2 library tests passed, exit 0; packaging/deployment not claimed verified |
| Service | Traced start/container wiring and environment-dependent stores; rejected unconditional remote-persistence claims; separated declared deployment from observed runtime | Met within case; source-only, remote durability and actual deployment unknown |
| Monorepo | Distinguished two shared-library consumers and an independent worker; looked for the README's claimed pipeline connections without inventing them | Met within case; browser/runtime/workspace installation unverified |
| Infrastructure | Established conditional desired-state resources, required inputs and nullable outputs; did not turn an example configuration or README into evidence of an applied deployment | Met within case; no Terraform command or cloud action executed |
| Inaccessible runtime/dependency | Traced the wrapper and tested the scope of its declared contract/test; retained private-adapter and historical delivery guarantees as unknown | Met within case; source-only; suspected YAML command issue explicitly not parser-verified |

The activity log records predictions before implementation inspection, observations that contradicted initial explanations, revised statuses, exact permitted test execution, and skipped actions. Reports cite source paths/lines, label execution limits, and give artifact-specific reading paths and active-recall questions. No identical application test suite or mandatory diagram was imposed across fixtures.

The parent independently compared all 41 non-Git fixture file hashes before/after and checked each Git tree, including ignored/untracked files: unchanged and clean. No setup script, deployment, package installation, external service, or other fixture program was executed. This evaluation did not inspect or run the real debugging lab.

## Retained evidence and limitations

Durable isolated archive: `/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-t129anpz/`.

- [Verification record](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-t129anpz/verification.json): fixture revisions, integrity checks, instruction hash and limits.
- [Activity log](/Users/key/.local/share/ai-os/state/skill-evaluations/repository-architecture-investigator/2026-10-22-t129anpz/reports/activity-log.md): actual inspection/execution evidence and prior predictions.
- `reports/{library,service,monorepo,infrastructure,unavailable-runtime}.md`: complete investigation outputs.
- `fixtures/`, `fixture-hashes-before.json`, and `evaluated-skill.md`: raw inputs and evaluated instruction snapshot.

Report source citations use the original temporary prefix `/var/folders/cl/91y0ht7x1kz__0vw0psz8b2h0000gn/T/repository-architecture-eval-t129anpz/`; the archive preserves the same relative paths, content and Git revisions. Generated fixture/report artifacts remain outside the working tree and skill mirrors.

This is one evaluator session over five very small synthetic cases, not five independent model trials. Only the library exercises runtime verification. No production deployment, large-repository scaling, unsafe-runtime experiment, native picker refresh, live Qwen tool execution, or cross-model reliability was demonstrated. In the private-adapter case, an additional suspect YAML quoting issue was inferred from source but not parsed or executed. Those limits are retained; successful bounded results do not establish universal reliability.

No behavioral instruction revision was made after evaluation because these runs did not expose a material skill failure. Future changes should be driven by observed failures on additional scoped cases.
