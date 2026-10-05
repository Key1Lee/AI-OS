# Systems Registry + Validation Harness

A small map of independent systems, their ownership, current paths, and proven
connections. Start at [SYSTEMS.md](../SYSTEMS.md); the concise layer guide is
[ARCHITECTURE.md](../ARCHITECTURE.md). This folder holds metadata and checks,
not copies of projects, databases, secrets, or a new application.

## Reading the entries

Each file in `registry/` is one system's ID card. Its `name` is the stable ID
used in `depends_on` and `consumed_by`. All local paths are relative to the
AI-OS root, including `entrypoints`, `public_interfaces`, `contracts`, and
`documentation`. Absolute paths are also accepted for proven external local
locations. Entrypoints and interfaces point to their existing source files;
`state_owned` describes responsibility rather than requiring state files to
exist. Do not initialize a database just to fill this map.

Test commands run from the system's `path`, using that project's own environment
and instructions. They are existing check definitions, not records of passing
runs. A `health_check` is a command or null; none has been confirmed yet.
`lifecycle: UNKNOWN` avoids assuming that existing code is operational.

`UNKNOWN`, null health checks, and empty lists preserve unconfirmed metadata.
An empty dependency list means no registered code/runtime edge was proven;
it is not a claim that no conceptual or future connection is possible. Current
`depends_on` / `consumed_by` lists describe implemented sibling code/runtime
use. Optional artifact compatibility is explained in `SYSTEMS.md` and each
project's existing interface files. FDE's existing local integration inventory
and AI-OS's source-route registry serve different purposes and remain intact.

For a normal task: locate its owner, read only that YAML and local guidance,
inspect the relevant contract/source, and expand to consumers only when the
change crosses a boundary. Keep application checks in the owning project.

## Run the registry check

Python is already used by AI-OS. YAML parsing uses one dependency, PyYAML, in
an isolated environment; shared runtime configuration stays unchanged.
From the AI-OS root, setup is:

```sh
python3 -m venv systems-registry/.venv
systems-registry/.venv/bin/python -m pip install -r systems-registry/requirements.txt
```

The environment was created during this setup and is ignored by the existing
root `.gitignore`. Run:

```sh
systems-registry/.venv/bin/python systems-registry/scripts/validate_registry.py
systems-registry/.venv/bin/python -m unittest discover -s systems-registry/tests -v
```

The validator resolves its default paths from the script location, so it also
works from another working directory when called by absolute path. Optional
`--registry-dir` and `--workspace-root` select fixture locations.

The check safely parses every `.yaml` / `.yml`, rejects duplicate YAML keys and
system names, checks required fields and basic types, verifies known local
paths, and resolves `depends_on` and `consumed_by` to registered system names.
Unknown values are allowed. Failure returns a nonzero exit code. Commands are
metadata only; the validator never runs application tests or health checks.
Passing this check establishes registry consistency, not cross-system
compatibility or application readiness.

## Minimal validation areas

| Folder | Future purpose |
| --- | --- |
| `validation/architecture/` | System boundary and metadata checks; the initial executable check is `scripts/validate_registry.py`. |
| `validation/contracts/` | Compatibility between explicitly connected interfaces. |
| `validation/integration/` | Important workflows spanning multiple systems. |
| `validation/smoke/` | Quick checks that an individual system can execute basic behavior. |

These four directories currently contain only `.gitkeep` placeholders. Actual
cross-system contract definitions will be added only when a real interface
needs them; see [contracts/README.md](contracts/README.md).
