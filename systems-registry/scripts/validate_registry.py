#!/usr/bin/env python3
"""Check the Systems Registry's metadata, local paths, and system references."""

import argparse
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print(
        "PyYAML is required; install systems-registry/requirements.txt first.",
        file=sys.stderr,
    )
    raise SystemExit(2)


class UniqueKeyLoader(yaml.SafeLoader):
    """Use safe YAML parsing while rejecting ambiguous duplicate keys."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    None, None, "mapping key must be hashable", key_node.start_mark
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key: {key!r}", key_node.start_mark
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


TEXT_FIELDS = ("name", "purpose", "path", "lifecycle")
LIST_FIELDS = (
    "owns", "does_not_own", "entrypoints", "public_interfaces", "depends_on",
    "consumed_by", "contracts", "state_owned", "documentation",
)
PATH_FIELDS = ("entrypoints", "public_interfaces", "contracts", "documentation")
TEST_KINDS = ("unit", "smoke", "contract", "integration")
REQUIRED_FIELDS = (*TEXT_FIELDS, *LIST_FIELDS, "tests", "health_check")


def is_known(value):
    """Empty and UNKNOWN values deliberately carry no resolvable reference."""
    return isinstance(value, str) and bool(value.strip()) and value != "UNKNOWN"


def local_path(value, workspace_root):
    path = Path(value)
    return path if path.is_absolute() else workspace_root / path


def validate_registry(registry_dir, workspace_root):
    """Return (entry count, errors); inspect only registry-owned metadata."""
    registry_dir, workspace_root = Path(registry_dir), Path(workspace_root)
    errors = []
    if not registry_dir.is_dir():
        return 0, [f"{registry_dir}: registry directory does not exist"]
    files = sorted(
        path for path in registry_dir.iterdir()
        if path.is_file() and path.suffix.lower() in (".yaml", ".yml")
    )
    if not files:
        return 0, [f"{registry_dir}: no registry YAML files found"]
    entries = []
    names = {}
    for file in files:
        def error(field, message):
            errors.append(f"{file}: {field}: {message}")

        try:
            with file.open(encoding="utf-8") as stream:
                entry = yaml.load(stream, Loader=UniqueKeyLoader)
        except (yaml.YAMLError, UnicodeError, OSError, ValueError) as exc:
            error("YAML", str(exc))
            continue
        if not isinstance(entry, dict):
            error("YAML", "entry must be a mapping")
            continue
        entries.append((file, entry))
        for field in REQUIRED_FIELDS:
            if field not in entry:
                error(field, "required field is missing")
        for field in TEXT_FIELDS:
            if field in entry and (
                not isinstance(entry[field], str) or not entry[field].strip()
            ):
                error(field, "must be a nonempty string (UNKNOWN is allowed)")
        for field in LIST_FIELDS:
            if field in entry and (
                not isinstance(entry[field], list)
                or any(not isinstance(item, str) for item in entry[field])
            ):
                error(field, "must be a list of strings (an empty list is allowed)")
        tests = entry.get("tests")
        if "tests" in entry and not isinstance(tests, dict):
            error("tests", "must be a mapping of test kinds to command lists")
        elif isinstance(tests, dict):
            for kind in TEST_KINDS:
                if kind not in tests:
                    error(f"tests.{kind}", "required field is missing")
                elif not isinstance(tests[kind], list) or any(
                    not isinstance(command, str) for command in tests[kind]
                ):
                    error(f"tests.{kind}", "must be a list of command strings")
        if entry.get("health_check") is not None and not isinstance(
            entry["health_check"], str
        ):
            error("health_check", "must be null or a command string")
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            if name in names:
                error("name", f"duplicate system name {name!r}; first in {names[name]}")
            else:
                names[name] = file
        path = entry.get("path")
        if is_known(path) and not local_path(path, workspace_root).is_dir():
            error("path", f"system directory does not exist: {path}")
        for field in PATH_FIELDS:
            values = entry.get(field)
            if isinstance(values, list):
                for index, value in enumerate(values):
                    if is_known(value) and not local_path(value, workspace_root).exists():
                        error(f"{field}[{index}]", f"local path does not exist: {value}")
    for file, entry in entries:
        for field in ("depends_on", "consumed_by"):
            values = entry.get(field)
            if isinstance(values, list):
                for index, name in enumerate(values):
                    if is_known(name) and name not in names:
                        errors.append(
                            f"{file}: {field}[{index}]: unknown system name {name!r}"
                        )
    return len(files), errors


def main(argv=None):
    script = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-dir", type=Path, default=script.parent.parent / "registry")
    parser.add_argument("--workspace-root", type=Path, default=script.parents[2])
    args = parser.parse_args(argv)
    try:
        count, errors = validate_registry(args.registry_dir, args.workspace_root)
    except OSError as exc:
        print(f"Registry validation failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"Registry validation failed: {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Registry validation passed: {count} system(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
