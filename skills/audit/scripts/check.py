from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next((parent for parent in Path(__file__).resolve().parents
             if (parent / "py_dev" / "skill_audit.py").is_file()
             and (parent / "skills" / "catalog.toml").is_file()), None)
if ROOT is None:
    raise SystemExit("Cannot locate the AI-OS root from the audit script")
sys.path.insert(0, str(ROOT))
from py_dev.skill_audit import audit  # noqa: E402
from py_dev.skill_state import _atomic_json, _scope_dir  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--save", action="store_true", help="Explicitly save a dated private report")
    args = parser.parse_args()
    report = audit(ROOT, project=args.project, live=args.live)
    if args.save:
        folder = _scope_dir(ROOT, args.project) / "audits"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = folder / f"{stamp}-audit.json"
        _atomic_json(path, report)
        report["saved_report"] = str(path)
    print(json.dumps(report, indent=2))
    if any(item["classification"] == "confirmed defect" for item in report["findings"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
