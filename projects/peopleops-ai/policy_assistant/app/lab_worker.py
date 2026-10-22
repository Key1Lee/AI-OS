"""Fixed local test commands, isolated from the portal's runtime data and reports."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = {"unit": ["tests/unit"], "integration": ["tests/integration"], "security": ["tests/security"],
          "evaluations": ["tests/unit", "tests/integration", "tests/security", "tests/end_to_end", "tests/performance"]}


def run_worker(suite, output):
    """Run real pytest, then full evaluations when selected, with job-specific artifacts."""
    output.mkdir(parents=True, exist_ok=True)
    os.environ["HR_TEST_REPORT_DIR"] = str(output)
    os.environ["COVERAGE_FILE"] = str(output/".coverage")
    command = [sys.executable, "-m", "pytest", *SUITES[suite], "-o", "addopts=", "-q", "--cov",
               "--cov-report=json:"+str(output/"coverage.json"), "--cov-report=xml:"+str(output/"coverage.xml"),
               "--junitxml="+str(output/"tests.xml")]
    status = subprocess.call(command, cwd=ROOT)
    if status or suite != "evaluations":
        return status
    return subprocess.call([sys.executable, "-m", "evals.run_evaluations", "--output", str(output),
                            "--coverage", str(output/"coverage.json"), "--test-evidence", str(output/"test-run.json")], cwd=ROOT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=SUITES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run_worker(args.suite, args.output))
