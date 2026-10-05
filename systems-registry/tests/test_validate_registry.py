"""Focused checks for registry consistency; no system tests are executed."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_registry.py"
SPEC = importlib.util.spec_from_file_location("validate_registry", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def valid_entry(name="example"):
    return {
        "name": name,
        "purpose": "An example system.",
        "owns": [],
        "does_not_own": [],
        "path": "UNKNOWN",
        "entrypoints": [],
        "public_interfaces": [],
        "depends_on": [],
        "consumed_by": [],
        "contracts": [],
        "state_owned": [],
        "tests": {kind: [] for kind in ("unit", "smoke", "contract", "integration")},
        "health_check": None,
        "documentation": [],
        "lifecycle": "active",
    }


class RegistryValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.registry = self.workspace / "registry"
        self.registry.mkdir()

    def write(self, entry=None, filename="example.yaml"):
        path = self.registry / filename
        path.write_text(yaml.safe_dump(entry if entry is not None else valid_entry()))
        return path

    def errors(self):
        return validator.validate_registry(self.registry, self.workspace)[1]

    def test_unknown_paths_and_empty_lists_are_valid(self):
        entry = valid_entry()
        entry["entrypoints"] = ["UNKNOWN", ""]
        entry["state_owned"] = ["descriptive state, not a filesystem path"]
        entry["tests"]["unit"] = ["python3 -m unittest discover -s tests -q"]
        self.write(entry)
        self.assertEqual(self.errors(), [])

    def test_empty_registry_is_rejected(self):
        self.assertIn("no registry YAML files", self.errors()[0])

    def test_missing_registry_directory_is_rejected(self):
        self.registry.rmdir()
        self.assertIn("registry directory does not exist", self.errors()[0])

    def test_all_yaml_files_are_parsed(self):
        self.write(filename="valid.yml")
        (self.registry / "broken.yaml").write_text("name: [unclosed")
        errors = self.errors()
        self.assertTrue(any("broken.yaml: YAML:" in error for error in errors))

    def test_yaml_entry_must_be_a_mapping(self):
        (self.registry / "example.yaml").write_text("- example\n")
        self.assertIn("entry must be a mapping", self.errors()[0])

    def test_duplicate_yaml_keys_are_rejected(self):
        path = self.write()
        with path.open("a") as stream:
            stream.write("name: replaced\n")
        self.assertIn("duplicate key: 'name'", self.errors()[0])

    def test_missing_required_fields_include_file_and_field(self):
        entry = valid_entry()
        del entry["purpose"]
        del entry["health_check"]
        self.write(entry)
        errors = self.errors()
        self.assertTrue(any("example.yaml: purpose: required field is missing" in error for error in errors))
        self.assertTrue(any("health_check: required field is missing" in error for error in errors))

    def test_wrong_field_types_and_empty_required_text_are_rejected(self):
        for field, value in (("name", ""), ("purpose", None), ("path", 42),
                             ("lifecycle", " "), ("owns", "items"),
                             ("state_owned", [42]), ("health_check", {})):
            with self.subTest(field=field):
                entry = valid_entry()
                entry[field] = value
                self.write(entry)
                self.assertTrue(any(f": {field}:" in error for error in self.errors()))

    def test_test_kinds_require_command_lists(self):
        for value in (None, {}, {"unit": "python test.py"},
                      {"unit": [42], "smoke": [], "contract": [], "integration": []}):
            with self.subTest(tests=value):
                entry = valid_entry()
                entry["tests"] = value
                self.write(entry)
                self.assertTrue(any(": tests" in error for error in self.errors()))

    def test_duplicate_system_names_are_rejected(self):
        self.write(filename="first.yaml")
        self.write(filename="second.yaml")
        self.assertTrue(any("duplicate system name 'example'" in error for error in self.errors()))

    def test_dependency_and_consumer_names_must_exist(self):
        entry = valid_entry()
        entry["depends_on"] = ["missing-dependency"]
        entry["consumed_by"] = ["missing-consumer"]
        self.write(entry)
        errors = self.errors()
        self.assertTrue(any("depends_on[0]: unknown system name" in error for error in errors))
        self.assertTrue(any("consumed_by[0]: unknown system name" in error for error in errors))

    def test_known_references_need_no_reciprocal_metadata(self):
        entry = valid_entry()
        entry["depends_on"] = ["other"]
        entry["consumed_by"] = ["other"]
        self.write(entry)
        self.write(valid_entry("other"), "other.yml")
        self.assertEqual(self.errors(), [])

    def test_known_system_path_must_be_a_directory(self):
        entry = valid_entry()
        entry["path"] = "missing-project"
        self.write(entry)
        self.assertTrue(any("path: system directory does not exist" in error for error in self.errors()))
        (self.workspace / "missing-project").write_text("a file is not a system directory")
        self.assertTrue(any("path: system directory does not exist" in error for error in self.errors()))

    def test_local_path_lists_must_exist(self):
        entry = valid_entry()
        for field in ("entrypoints", "public_interfaces", "contracts", "documentation"):
            entry[field] = [f"missing/{field}"]
        self.write(entry)
        errors = self.errors()
        for field in ("entrypoints", "public_interfaces", "contracts", "documentation"):
            self.assertTrue(any(f"{field}[0]: local path does not exist" in error for error in errors))

    def test_relative_and_absolute_local_paths_are_valid(self):
        source = self.workspace / "source"
        source.mkdir()
        (source / "main.py").write_text("# fixture\n")
        entry = valid_entry()
        entry["path"] = "source"
        entry["entrypoints"] = ["source/main.py", str(source / "main.py")]
        entry["documentation"] = ["source"]
        self.write(entry)
        self.assertEqual(self.errors(), [])

    def test_invalid_encoding_reports_an_error_without_a_crash(self):
        (self.registry / "example.yaml").write_bytes(b"name: \xff")
        self.assertIn("YAML:", self.errors()[0])

    def test_invalid_yaml_timestamp_reports_an_error_without_a_crash(self):
        (self.registry / "example.yaml").write_text("name: 2026-99-99\n")
        self.assertIn("YAML:", self.errors()[0])

    def test_unsafe_yaml_tags_are_rejected(self):
        (self.registry / "example.yaml").write_text("name: !!python/tuple [example]\n")
        self.assertIn("YAML:", self.errors()[0])

    def test_cli_default_paths_are_independent_of_working_directory(self):
        area = self.workspace / "systems-registry"
        scripts = area / "scripts"
        scripts.mkdir(parents=True)
        script = scripts / SCRIPT.name
        script.write_text(SCRIPT.read_text())
        self.registry.rename(area / "registry")
        self.registry = area / "registry"
        self.write()
        result = subprocess.run([sys.executable, str(script)], cwd="/", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Registry validation passed: 1 system(s).", result.stdout)

    def test_cli_fixture_options_and_failure_exit_code(self):
        self.write()
        (self.registry / "bad.yml").write_text("name: [unclosed")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--registry-dir", str(self.registry),
             "--workspace-root", str(self.workspace)],
            cwd="/", text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("bad.yml: YAML:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
