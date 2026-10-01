"""Safely generate Codex and Claude Skill mirrors from canonical skills/."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = ".aios-generated.json"
INCLUDE = {"SKILL.md", "references", "scripts", "assets", "agents"}


def files(folder: Path) -> dict[str, str]:
    result = {}
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if path.is_file() and relative.parts[0] in INCLUDE:
            result[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def expected_names() -> list[str]:
    import tomllib

    with (ROOT / "skills" / "catalog.toml").open("rb") as stream:
        return sorted(tomllib.load(stream)["skills"])


def sync(check: bool = False) -> list[str]:
    problems = []
    names = expected_names()
    for mirror in (ROOT / ".agents" / "skills", ROOT / ".claude" / "skills"):
        if mirror.exists():
            for item in mirror.iterdir():
                if item.is_dir() and item.name not in names:
                    problems.append(f"unexpected mirror Skill: {item}")
        for name in names:
            canonical = ROOT / "skills" / name
            destination = mirror / name
            desired = files(canonical)
            if not desired or "SKILL.md" not in desired:
                problems.append(f"missing canonical Skill: {canonical}")
                continue
            if check:
                if files(destination) != desired:
                    problems.append(f"Skill mirror differs from canonical: {destination}")
                continue
            if destination.exists():
                marker = destination / MARKER
                if not marker.is_file():
                    problems.append(f"unmanaged Skill mirror; inspect before replacing: {destination}")
                    continue
                try:
                    recorded = json.loads(marker.read_text(encoding="utf-8"))["files"]
                except (ValueError, KeyError, OSError):
                    recorded = None
                if files(destination) != recorded:
                    problems.append(f"manually modified Skill mirror; reconcile first: {destination}")
                    continue
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)
            for relative in desired:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(canonical / relative, target)
            (destination / MARKER).write_text(json.dumps({"canonical": f"skills/{name}", "files": desired}, indent=2) + "\n", encoding="utf-8")
    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = sync(args.check)
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    print("Skill mirrors match canonical skills" if args.check else "Skill mirrors synchronized")
