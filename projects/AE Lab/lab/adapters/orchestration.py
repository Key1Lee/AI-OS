import json
import os
import subprocess
from .bridge import ROOT, AdapterError, project_path

class NativeOrchestrationAdapter:
    def schedule(self, run_id: str, fail_after_rows: int | None) -> dict:
        project = project_path("orchestration")
        tsx = project / "node_modules/.bin/tsx"
        if not tsx.is_file():
            raise AdapterError(f"Orchestration runtime missing; run npm ci in {project}")
        payload = {"run_id": run_id, "fail_after_rows": fail_after_rows, "project": str(project)}
        try:
            result = subprocess.run([str(tsx), str(ROOT / "lab/adapters/workers/orchestration.ts")],
                                    input=json.dumps(payload), text=True, capture_output=True,
                                    cwd=project, env=dict(os.environ), timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdapterError(f"Orchestration bridge failed: {exc}") from exc
        if result.returncode:
            raise AdapterError(f"Orchestration: {result.stderr[-3000:]}")
        return json.loads(result.stdout)
