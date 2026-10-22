# Cloud development and interactive engineering practice

AI-OS is published at [Key1Lee/AI-OS](https://github.com/Key1Lee/AI-OS).
The repository is private. GitHub stores the code, Codex Cloud provides remote
execution, and an authorized GitHub connection lets ChatGPT retrieve repository
content. Verify these three capabilities separately.

## Shared environment

Use Python 3.11 or newer (CI uses 3.12). From the clone root:

```sh
bash scripts/cloud/setup.sh
bash scripts/cloud/check.sh
```

Setup creates `.venv/cloud`, installs the shared package and the pinned registry
parser, and requires package-download access. Checks run shared unit tests,
Skill mirror validation, and registry validation. The scripts resolve the clone
root without a machine-specific absolute path. The virtual environment is
ignored by Git. Run commands with `.venv/cloud/bin/python`; activation in a
setup shell does not necessarily persist into a later task.

Read `SYSTEMS.md`, the owning registry YAML, and local `AGENTS.md` before project
work. Install that project's declared dependencies in its own environment and
run its declared tests. Use frozen lockfiles when provided. Node projects need
the versions and package manager their manifests specify. This shared baseline
does not install every independent project or prove their integration behavior.
Keep sibling projects at their existing relative paths for adapters that use them.

Local model servers, macOS launchers, external providers, n8n instances,
Docker-based learning labs, PostgreSQL, and production integrations require
separate setup. Do not equate their absence with a failed unit test or silently
switch to a live service. Debugging lab upstream checkouts and captured local
evidence remain excluded by project policy; their pinned source retrieval
instructions are in their own runbooks.

## Connect Codex Cloud

1. Sign in with the intended personal account. Open Settings → Codex Cloud →
   Environments → Create environment, or Work in → Cloud → Select environment →
   Create environment.
2. Connect GitHub if prompted. In GitHub's authorization flow, allow only
   `Key1Lee/AI-OS`. Review permissions and complete authorization yourself.
3. Select this repository. Ask the setup conversation to run
   `bash scripts/cloud/setup.sh`, then `bash scripts/cloud/check.sh`, using
   Python 3.12. In an interface with a manual setup-script field, enter
   `bash scripts/cloud/setup.sh`; the verification command is separate.
4. Keep the environment personal/private. No API secrets are needed for the
   shared baseline. Allow dependency downloads during setup; start with agent
   internet access disabled and enable only what a specific task requires.
5. Inspect the setup logs, then publish the prepared environment. Start a fresh
   task from `main` to verify the published state. Republish after dependency
   setup changes; existing tasks can retain older state.

Use this remote verification request:

```text
Verify the published AI-OS environment without changing tracked files.
Report pwd, git rev-parse HEAD, Python version, and git status --short.
Run bash scripts/cloud/check.sh and record each command's exit status and output.
Read SYSTEMS.md and py_dev/router.py and identify the routing entrypoint.
Do not call external model providers or start project services.
Report skipped checks explicitly. Do not claim all independent projects passed.
```

Acceptance requires a cloud task URL/ID, the expected Git commit, actual passing
logs, and a clean tracked working tree. Local or GitHub Actions success cannot
substitute for this evidence. See [official cloud environment guidance](https://learn.chatgpt.com/docs/environments/cloud-environments)
and the [legacy setup-script interface](https://learn.chatgpt.com/docs/environments/cloud-environment).

## Connect personal ChatGPT

Open the personal account's Settings → Apps or Plugins, find GitHub, and use
Connect or the plugin setup flow. Complete GitHub authorization and select only
`Key1Lee/AI-OS`. Account, workspace, and interface availability can differ. A
connection available in Codex does not independently prove access in another
ChatGPT conversation. See [official connected-app guidance](https://learn.chatgpt.com/docs/dots/computers-and-apps).

In a new personal ChatGPT conversation, select or mention the GitHub integration
and ask:

```text
Use the connected private repository Key1Lee/AI-OS. Retrieve SYSTEMS.md,
architecture/cloud-development.md, and py_dev/router.py from main.
Quote one short distinctive passage from each and cite its repository path.
For py_dev/router.py, identify a real function and explain its role.
Report the branch and commit if the tool exposes them. If access fails, say so;
do not infer contents from the repository name, previous chats, or this prompt.
```

Check the cited passages against GitHub. This proves actual retrieval in that
conversation. A repository URL, installed app, or remembered architecture does
not prove retrieval. Repository access does not automatically execute tests or
keep every file in model context. Use a tool-capable coding environment for
execution and changes. There is no repository setting that can force another
personal ChatGPT account to authorize GitHub or grant a missing product feature.

## Continuous use

Before each session, fetch `origin`, record the branch and commit, and inspect
local changes. Work on a `codex/` branch; inspect the diff, run the owning
project's checks, and push the branch for review. The shared GitHub Actions
workflow checks each pushed candidate, while project CI remains project-owned.
Pull approved changes before the next session. Do not force-push over local
learner work or commit local credentials, caches, dependency stores, or databases.

## Reusable coaching prompt

```text
Act as my Principal Software Engineer and DevOps coach for Key1Lee/AI-OS.
Use the connected repository as evidence. Confirm access by retrieving SYSTEMS.md
and naming the branch/commit when available. If you cannot retrieve source, stop
the code-specific interview and tell me which access is missing.

Read the owning system's registry YAML and local AGENTS.md. Honor its learner
boundaries, current progress records, and no-spoiler rules. Start from my current
task when one is recorded; otherwise ask ONE question to choose a project and
level. Do not assume an unfinished exercise is a product bug to fix for me.

Ask exactly ONE question per turn and wait for my answer. Ground each question
in actual file paths, functions, tests, or contracts. Progress through business
invariants, architecture, execution flow, tests, failure diagnosis, and operational
tradeoffs. Challenge assumptions and ask what evidence would falsify my claim.

For debugging, first present only realistic symptoms and known constraints.
Label a tabletop simulation explicitly. Do not invent observed logs or tests.
Reveal evidence incrementally in response to my chosen measurements. Do not
reveal the cause, historical fix, leading hints, solution code, or an experiment
that gives away the answer. Ask me to predict results before experiments.

Run experiments only when I request them and the environment permits them.
Keep executable simulations in an isolated disposable branch with synthetic
data, preserve learner-owned code, and never inject faults into production or
silently modify an authentic pinned challenge. Honor project-specific protocols.

After each answer, briefly assess correctness, evidence, and reasoning. Score
each 0–2, explain the score without disclosing the solution, and ask ONE follow-up
on the weakest point. Track investigation quality separately from whether a fix
works. Give a hint or solution only when I explicitly request one; provide the
smallest hint first. Do not implement my exercise or advance progress for me.

At session end, provide a compact ledger: commit, files examined, hypotheses,
commands actually run with outcomes, unresolved questions, scores, and next
question. Return this in chat unless I ask to save it. I can paste it into the
next session; do not assume persistent memory or automatic repository syncing.
```

## Verification record 2026-10-23

| Criterion | Observed evidence | Status |
| --- | --- | --- |
| Private GitHub repository | GitHub CLI and connected GitHub metadata report private visibility | Supported |
| Shared baseline locally | Fresh `.venv/cloud`; 119 unit tests passed; mirrors match; 11 registry entries validate | Supported locally |
| Complete Git synchronization | Compare final local commit and `refs/heads/main` after push | Pending publication |
| Linux execution | Shared GitHub Actions workflow added; inspect its actual run after push | Pending CI |
| Codex Cloud execution | Create-environment selector reported “GitHub connections couldn’t load” after retry; CLI listed no tasks | Blocked on cloud connection |
| Personal ChatGPT retrieval | Must execute the retrieval challenge in the personal ChatGPT conversation | Unverified |
| Every independent project executes remotely | Requires project-specific environments and checks | Unverified |

Gitleaks 8.30.1 scanned the four existing Git commits and the candidate snapshot.
Its 10 history findings were source checksums. Its 34 snapshot findings were
10 checksums, 7 hashes of explicitly synthetic demo tokens, and 17 documentation
examples using demo/fake headers. All were reviewed; no real secret was found
among these matches. This is a reviewed scan with false positives, not a claim
that the scanner reported zero findings. Local `.env` files and dependency
caches were excluded. The remote was public before this task; changing visibility
does not revoke any copies previously downloaded.
