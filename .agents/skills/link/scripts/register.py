from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from py_dev.source_registry import SourceRegistry  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--project")
    parser.add_argument("--id")
    parser.add_argument("--authority", default="original")
    parser.add_argument("--freshness-days", type=int)
    parser.add_argument("--related", action="append", default=[], help="ID of an existing related route")
    args = parser.parse_args()
    record = SourceRegistry(ROOT).register(args.target, args.purpose, project=args.project, source_id=args.id, authority=args.authority, freshness_days=args.freshness_days, related_ids=tuple(args.related))
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
