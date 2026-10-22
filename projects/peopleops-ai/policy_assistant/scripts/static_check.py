"""Check the new enterprise runtime without reformatting the preserved policy API."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULES = ["main", "auth", "identity", "intent_router", "models", "mock_store", "orchestrator", "permissions", "rag_search", "response_builder", "settings", "workday_client", "audit", "rules", "diagnostics", "enterprise_data", "test_runner", "lab_worker"]
targets = [str(ROOT / "app" / (name+".py")) for name in MODULES]
targets += [str(ROOT / directory) for directory in ("ingestion", "evals", "tests/unit", "tests/integration", "tests/security", "tests/end_to_end", "tests/performance")]
raise SystemExit(subprocess.call([sys.executable,"-m","ruff","check","--select","E9,F",*targets],cwd=ROOT))
