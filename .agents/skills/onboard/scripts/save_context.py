from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from py_dev.skill_state import save_context  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project")
    parser.add_argument("--scope", choices=("global",), help="Use global only when no project is supplied")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    if bool(args.project) == bool(args.scope):
        parser.error("Specify exactly one of --project or --scope global")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    path = save_context(ROOT, project=args.project, facts=data["facts"], confirmed=data.get("confirmed") is True, source=data.get("source", "user"))
    print(path)


if __name__ == "__main__":
    main()
