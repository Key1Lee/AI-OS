# Phase 1 independent verification

## Revalidation — 2026-10-04

**Outcome: VERIFIED for the existing local, tutor-assisted Phase 1 contract.**
The current attachment exactly matches `docs/master-prompt.md`. Product source
and scenario hashes still match the independently inspected snapshot below.
This pass inspected the existing implementation before reusing it; it did not
rebuild the project or create a second FDE runtime.

The work refreshed AE Lab's reference entry against its current README, CLI,
contracts, adapter and Makefile, and preserved the earlier independent probe at
`scripts/verify_phase1.py`. The probe now resolves the project relative to its
own path rather than a machine-specific absolute path. Its previously unreachable
no-op statement was removed. Test answers and reference SQL remain instructor-only.
The README and project guidance now describe that verification entrypoint.

After those changes, a read-only product verification pass ran:

| Check | Observed evidence | Result |
|---|---|---|
| `python3 -m unittest discover -s tests -v` | 27 tests passed; complete simulator, SQL, disclosure, persistence, review and recall behavior exercised | PASS |
| `python3 scripts/verify_phase1.py` | 245 assertions across 133 public CLI commands; one scenario, all 11 boxes, 13 evidence cards and 11 recall prompts | PASS |
| Independent alternative implementation within the probe | Eight baseline cases and sixteen replay cases passed; broken artifacts failed before repair | PASS |
| Disclosure and progression controls | Locked reads, premature build, private-field canaries, stale-artifact deployment and invalid recall reviews rejected or withheld as specified | PASS |
| Reset within temporary profiles | Exact opening and fixture reproduced; prior state and learner SQL archived byte-for-byte | PASS |
| `sh -n fde` and `sh -n Start-FDE-Lab.command` | Both launchers parsed and had executable permissions; CLI probe also entered and exited the shell | PASS |
| Reference inventory inspection | Every declared source path exists; execution remains disabled; sibling runtimes were not called | PASS |
| Real learner profile | Still DISCOVERY with zero released artifacts, submissions and reviews; verification profiles were temporary and removed | PASS |

The criterion-to-evidence map and limitations below still apply. These are
synthetic behavior checks, not assessments of the user's competence. No live model,
warehouse, external deployment or sibling execution was verified. This revalidation
was performed in a separate read-only phase of the same task, not by a newly
delegated agent. The original independently authored probe is preserved unchanged
apart from the portability and explanatory edits described above.

## Original independent inspection — 2026-10-03

**Outcome: VERIFIED for the documented local, tutor-assisted Phase 1.**
Inspected and executed on 2026-10-03 with Python 3.13.0 on Darwin arm64.
No remaining material failure was observed within this scope. This verdict does
not establish learner competence, automated semantic assessment or production readiness.

The controlling source is the user's pasted Forward Deployment Engineering Lab
request, especially sections 75–79, with the first-slice interpretation recorded in
[requirements](requirements.md). Verification followed the shared
[verification guidance](../../../architecture/verification.md).

Product code and tests were inspected read-only. The verifier had earlier authored
the descriptive integration inventory, then adopted a read-only product verification
role. Its independent probes used temporary profiles; no real learner answers,
reviews, mastery records or sibling runtime calls were created.

## Executed evidence

From the FDE Lab project root:

```sh
python3 -m unittest discover -s tests -v
sh -n fde
sh -n Start-FDE-Lab.command
python3 /tmp/fde-independent-verifier.py
```

- Project suite: **27 tests passed**. Coverage includes contracts, gate failures,
  persistence, SQL counterexamples, bounded execution, incident reproduction,
  stale deployment artifacts, recall through separate CLI processes and reassessment.
- Both shell entrypoints passed syntax checks. The actual `fde` launcher opened
  and exited the interactive shell with a temporary state directory.
- An independently authored CLI probe passed **245 assertions across 133 commands**,
  including command exit contracts. It used an alternative SQL implementation
  without importing the product tests' repair: eight baseline variations and
  sixteen replay variations passed. The injected artifact failed before repair.
- Every disposable learner profile was removed after the probes. The temporary
  verifier script is local verification evidence, not part of the shipped lab.

## Criterion-to-evidence map

| Required criterion | Evidence observed | Status |
|---|---|---|
| One Northstar scenario and ambiguous first opening | One scenario loaded; exact opening ended with the requested open question. Fresh state contained no released artifacts, submissions or reviews. | Supported |
| Requested, prerequisite-gated evidence | Locked investigation and direct evidence reads failed without modifying saved state. An unrelated question released nothing; a multi-topic question released one selected topic. All 13 cards were reachable through their valid prerequisites. | Supported |
| No premature instructor answer projection | Source inspection and separate private-field canary probes covered opening, diagram, all boxes, progress, map and log. Public projections withheld instructor-only fields. The normal opening did not invoke hint or solution paths. | Supported |
| Learner reasoning, challenge and feedback | CLI preserved the exact submitted hypothesis and returned a falsification question, feedback scaffold and rubric. Answers remained ungraded until an attributed review. Tutor guidance requires assessment of the actual answer and one missing causal link. | Supported for tutor-assisted operation |
| Architecture visualization and technical internals | The current transaction-to-answer diagram and all 11 component views were exercised. Each box supplied a local diagram, internals and a causal question. | Supported |
| Design, implementation and meaningful verification | Unreviewed design blocked build. Build produced a broken starter, fixture and task without a repair. Starter failed; independently authored SQL passed varied inputs against the Python oracle. Hardcoded and unsafe-query controls passed in the suite. | Supported |
| Introduced failure and learner debugging | Failure injection preserved the learner's original artifact, created a separate branch, and produced an executable failed replay check. Logs remained unreleased until requested. Repair passed 16 cases before the debugging/readiness gates opened. | Supported |
| Phase gates and artifact integrity | Full public CLI flow traversed discovery through retrospective. Early build/deploy were rejected. Editing the tested artifact blocked deployment without changing saved state; a new passing test enabled the simulated pilot. | Supported |
| Customer measurement | Pilot evidence was available only after rollout and came from the frozen scenario. Its baseline matched discovery evidence. Measurement and explanation remained saved, cited, tutor-reviewed learner tasks. | Supported for synthetic evidence |
| Persistent recall, attributed reviews and conservative progress | All 11 recall prompts were exercised through separate processes. Pending prompts remained stable; answers retained prompt IDs. Mismatched concept reviews failed atomically. One answer or repeated reviews did not fabricate mastery. | Supported |
| Reassessment and mastery regression | Distinct transfer prompts plus executable debugging supported scoped completion in synthetic attestations. A developing reassessment removed concept mastery and returned the engagement to retrospective. | Supported |
| Deterministic, non-destructive reset | Reset reproduced the exact opening, archived prior state and SQL byte-for-byte, cleared active answers/reviews, and rebuilt an identical fixture. Repeated reset produced identical started state. | Supported |
| Reference-only boundaries | Independent AST inspection found no imports of AI-OS or sibling execution packages. Registry execution remained disabled. The integration command listed references without calling siblings. | Supported |

## Corrected findings

Preflight inspection identified stale artifact approval, historical-review progress
inflation and inconsistent pilot baseline/population. Final probes confirmed current
artifact revalidation, review reassessment and coherent scenario-owned pilot facts.

The first independent CLI journey found a real recall-command crash: dispatch treated
the recall action as a reasoning submission. The implementation owner corrected the
dispatch and added a separate-process CLI regression test. The final independent
journey exercised every recall prompt and completed without the crash.

## Limits and handoff

The customer matcher recognizes configured whole words and phrases. A human or Codex
tutor supplies nuanced questioning and evaluates free-text reasoning. The checks
prove storage, disclosure and transition behavior; synthetic review inputs do not
prove a tutor's judgment or a learner's understanding. Tutor reviews are local
attestations with recorded identity and notes, not authenticated certifications.

No LLM runtime was configured or tested. Diagrams are text and Markdown. The SQL
runtime is a bounded local teaching exercise; real assistant behavior, warehouse
integration, infrastructure deployment, IAM enforcement, adoption and reliability
were not executed. Reading repository source can bypass learning gates, as documented.
These limits are explicit in the first-slice scope rather than hidden behind test passes.

Return to implementation and verification if product behavior, scenario facts or
contracts change. Keep future learner sessions and evidence separate from these
synthetic verification inputs.

Final inspected snapshot, SHA-256 prefixes:

| File | Prefix |
|---|---|
| `lab/cli.py` | `c08978d5c62a` |
| `lab/engine.py` | `c3ab2e4b8321` |
| `lab/contracts.py` | `ff0fa39260bc` |
| `lab/store.py` | `56bbb3df33d9` |
| `lab/exercise.py` | `bb09149b9a76` |
| `lab/scenarios/northstar.json` | `33eb6565ae11` |

Independent probe SHA-256:
`bb9f5ef81452cb5ad5a8beba7fd6c159a059e11da6542844b99f816f0354f75b`.
