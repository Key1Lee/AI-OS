from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from py_dev.skill_state import SkillInterviewStore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("start", "answer", "show", "pause", "resume", "complete"))
    parser.add_argument("--project")
    parser.add_argument("--session-id")
    parser.add_argument("--topic")
    parser.add_argument("--question")
    parser.add_argument("--answer")
    parser.add_argument("--status", choices=("unclassified", "confirmed", "hypothesis", "idea"), default="unclassified")
    args = parser.parse_args()
    store = SkillInterviewStore(ROOT)
    if args.action == "start":
        result = store.start(args.project, args.topic or "")
    else:
        if not args.session_id:
            parser.error("--session-id is required")
        if args.action == "answer":
            result = store.append(args.project, args.session_id, args.question or "", args.answer or "", args.status)
        elif args.action == "show":
            result = store.get(args.project, args.session_id)
        else:
            result = store.set_status(args.project, args.session_id, {"pause": "paused", "resume": "active", "complete": "complete"}[args.action])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
