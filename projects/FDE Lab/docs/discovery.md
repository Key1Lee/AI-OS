# Interaction guide

```text
Customer claim → workflow question → requested evidence → hypothesis → falsifying experiment
```

Normal entry: `./fde`. No menus precede the customer situation. Use `./fde shell` for repeated commands; `exit` saves already-recorded work and closes it. In Codex, ask naturally and the tutor records the equivalent lab actions.

| Intent | Command |
|---|---|
| Opening / resume | `next`, `scenario` |
| Contacts / boxes | `stakeholders`, `components` |
| Interview | `ask <stakeholder> "specific question"` |
| Inspect an artifact | `investigate "specific observation"` |
| Read released evidence | `evidence [id]` |
| Trace / explore | `diagram`, `open <component>`, `map` |
| Record reasoning | `hypothesis`, `answer`, `frame`, `requirements`, `design` |
| Execute / evaluate | `build`, `test [file]`, `evaluate` |
| Inject / diagnose | `break`, `debug`, `harden` |
| Simulate / measure | `deploy`, `measure`, `explain` |
| Recall / save feedback | `recall`, `answer --kind recall`, tutor `review` |
| Progress / history | `progress`, `log`, `end` |
| Hints / explicit solution | `hint`, `solution` |
| Fresh run preserving work | `reset` |

Prefix commands with `./fde` outside the shell. Reasoning commands accept quoted text or `--file /absolute/path`; stage submissions require `--evidence id1,id2`. Executed tests return an event ID that can also be cited. `--help` lists syntax.

Stakeholder questions match configured words/phrases and release one topic. Unknown questions request specificity instead of inventing facts. Evidence lists only already released cards. A locked artifact asks you to establish its upstream workflow. An unanswered question means unknown, not false.
