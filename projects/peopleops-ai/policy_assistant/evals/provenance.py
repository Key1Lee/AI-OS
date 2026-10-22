"""Bind release evidence to the exact local source, fixtures and evaluation labels."""
import hashlib
import json
from evals.common import ROOT


def fingerprint():
    paths = []
    for directory in ("app", "ingestion", "evals", "config", "mock_data", "requirements", "scripts", ".github/workflows", "tests/unit", "tests/integration", "tests/security", "tests/end_to_end", "tests/performance"):
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".yaml", ".jsonl", ".csv", ".html", ".css", ".js"))
    paths += [ROOT / name for name in ("pyproject.toml", "uv.lock", ".coveragerc", "tests/conftest.py")]
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def test_evidence(path, required_functions):
    if not path.is_file():
        return {"passed": False, "reason": "missing_test_run"}
    evidence = json.loads(path.read_text())
    executed = {row["nodeid"].split("::")[-1].split("[")[0] for row in evidence["tests"] if row["outcome"] == "passed"}
    missing = sorted(set(required_functions) - executed)
    valid = evidence["exit_status"] == 0 and evidence.get("source_matches_run_start", False) and evidence["source_fingerprint"] == fingerprint() and not missing
    return {"passed": valid, "exit_status": evidence["exit_status"], "passed_test_cases": sum(row["outcome"]=="passed" for row in evidence["tests"]),
            "missing_required_test_functions": missing, "source_matches": evidence["source_fingerprint"] == fingerprint(),
            "source_unchanged_during_tests": evidence.get("source_matches_run_start", False)}
