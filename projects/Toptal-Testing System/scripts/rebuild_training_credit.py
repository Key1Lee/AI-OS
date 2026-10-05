"""Preview or explicitly repair only terminal training's derived credit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.persistence import TrainingStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path, help="Explicit existing schema-2 training DB; never a default learner profile")
    parser.add_argument("--apply", action="store_true", help="Opt in to atomic derived-state repair after reviewing a preview")
    parser.add_argument("--expected-digest", help="The source_digest from the reviewed preview; required with --apply")
    parser.add_argument("--backup", type=Path, help="New backup path in an existing directory; default is a unique adjacent file")
    args = parser.parse_args()
    if args.apply and not args.expected_digest:
        parser.error("--apply requires --expected-digest from a reviewed preview")
    if not args.apply and (args.backup or args.expected_digest):
        parser.error("--backup/--expected-digest are only used with --apply")
    try:
        report = (
            TrainingStore.apply_credit_rebuild(args.database, expected_digest=args.expected_digest, backup_path=args.backup)
            if args.apply else TrainingStore.preview_credit_rebuild(args.database)
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(2, f"Credit rebuild refused: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
