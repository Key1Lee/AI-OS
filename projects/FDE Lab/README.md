# Forward Deployment Engineering Lab

Learn FDE work by investigating an ambiguous customer problem, defending a design, writing code, diagnosing failure, and proving customer value. Phase 1 contains one deep, synthetic Northstar Retail engagement.

```sh
./fde                  # immediately presents the customer opening
./fde shell            # persistent interactive command prompt
./fde stakeholders
./fde ask finance "What decision is this report supporting?"
./fde diagram
./fde open warehouse
./fde progress
```

Python 3.11+ is the only runtime dependency. No account, model, service, or sibling system is needed. Double-click `Start-FDE-Lab.command` on macOS to open the shell. The project launcher works without installation; optional installation with `python3 -m pip install -e .` exposes `fde` on your environment's PATH.

The CLI is a deterministic evidence simulator with explicit topic matching. It provides observations, component explanations, scaffolds, tests, and recall. A human or Codex tutor conducts nuanced conversation and evaluates free-text reasoning; the CLI never claims an answer is correct because it contains a keyword. See [the tutor workflow](docs/tutor.md).

```text
Customer question → specific evidence → learner hypothesis
        ↑                                   ↓
     recall ← failure/debug ← test ← learner implementation
                             ↑
                      reviewed design
```

Learner state and SQL work live in `progress/`, excluded from Git. `./fde reset` archives the current session and workspace before reproducing the same fresh opening and fixtures. For isolated runs use `./fde --state-dir /absolute/temporary/directory next`.

Commands and gates: [interaction guide](docs/discovery.md). Architecture and contracts: [architecture](docs/architecture.md). Reference-only capability map: [integrations](docs/integrations.md). Scope and acceptance: [requirements](docs/requirements.md). Check the implementation with:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_phase1.py
```

The second command repeats the full acceptance journey through the actual launcher in disposable profiles. Its scripted answers and reviews test behavior without adding learner credit to `progress/`.

Hidden facts and reference SQL exist in local instructor source, tests, and the acceptance script. They are withheld by the learner interface, not encrypted or inaccessible to someone reading the repository. Progress reviews record tutor identity and evidence; they are explicit local attestations, not authenticated certifications.
