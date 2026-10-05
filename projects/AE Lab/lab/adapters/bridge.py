from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECTS = ROOT.parent
PROJECTS = {
    "modeling": "Data Modeling System",
    "orchestration": "Data Orchestration System",
    "quality": "data-quality-contracts-system",
    "observability": "Data Observability System",
    "testing": "Toptal-Testing System",
}

class AdapterError(RuntimeError):
    pass

def project_path(system: str) -> Path:
    return Path(os.environ.get(f"AE_LAB_{system.upper()}_ROOT", DEFAULT_PROJECTS / PROJECTS[system])).resolve()

def invoke(system: str, payload: dict, worker: str | None = None) -> dict:
    project = project_path(system)
    python = Path(os.environ.get(f"AE_LAB_{system.upper()}_PYTHON", project / ".venv/bin/python"))
    script = ROOT / "lab/adapters/workers" / (worker or f"{system}.py")
    if not python.is_file() or not script.is_file():
        raise AdapterError(f"{system}: native runtime or bridge missing. See README setup and AE_LAB_{system.upper()}_ROOT/PYTHON.")
    paths = [project / "src", project / "services/modeling-engine/src", project]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, paths)), PYTHONDONTWRITEBYTECODE="1")
    try:
        result = subprocess.run([str(python), str(script)], input=json.dumps(payload), text=True,
                                capture_output=True, cwd=project, env=env, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"{system}: bridge failed: {exc}") from exc
    if result.returncode:
        raise AdapterError(f"{system}: native bridge failed: {result.stderr[-3000:]}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{system}: invalid bridge response") from exc
    if not isinstance(response, dict):
        raise AdapterError(f"{system}: bridge must return a JSON object")
    return response
