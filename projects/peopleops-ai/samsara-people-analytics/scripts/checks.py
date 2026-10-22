"""Run required host checks and preserve actual command outputs and exit codes."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
commands = [
    ["python3", "scripts/verify.py"],
    ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "*_test.py", "-v"],
    ["npm", "--prefix", "web", "test"],
    ["npm", "--prefix", "web", "run", "lint"],
    ["npm", "--prefix", "web", "run", "typecheck"],
    ["npm", "--prefix", "web", "run", "build"],
]
results = []
for command in commands:
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    results.append({"command": command, "exitCode": run.returncode, "stdout": run.stdout, "stderr": run.stderr})
    print(f"{'PASS' if run.returncode == 0 else 'FAIL'} {' '.join(command)}", flush=True)
    if run.returncode:
        print(run.stdout + run.stderr, flush=True)
passed = all(r["exitCode"] == 0 for r in results)
(ROOT / "evidence/checks.json").write_text(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "status": "PASS" if passed else "FAIL", "results": results}, indent=2) + "\n")
raise SystemExit(0 if passed else 1)
