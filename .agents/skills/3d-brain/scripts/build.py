"""Build a local metadata-only, rotatable view of explicitly selected routes."""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from py_dev.source_registry import SourceRegistry  # noqa: E402


def build(output: Path, *, project: str | None, include: list[str]) -> Path:
    if not include:
        raise ValueError("Select at least one approved route with --include")
    routes = {route["id"]: route for route in SourceRegistry(ROOT).list(project)}
    unknown = sorted(set(include) - routes.keys())
    if unknown:
        raise ValueError(f"Unknown source routes: {', '.join(unknown)}")
    selected = [routes[item] for item in dict.fromkeys(include)]
    nodes = []
    count = len(selected)
    for index, route in enumerate(selected):
        angle = index * math.pi * (3 - math.sqrt(5))
        height = 1 - (2 * index + 1) / count
        radius = math.sqrt(1 - height * height)
        target = route["target"]
        href = target if route["mechanism"] == "url" else "file://" + quote(target)
        nodes.append({"id": route["id"], "label": route["purpose"], "authority": route["authority"], "verified": route["verified"], "href": href, "related_ids": [item for item in route.get("related_ids", []) if item in include], "x": radius * math.cos(angle), "y": height, "z": radius * math.sin(angle)})
    data = json.dumps(nodes, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(f"AI-OS sources — {project or 'global'}")
    template = (Path(__file__).resolve().parents[1] / "assets" / "viewer.html").read_text(encoding="utf-8")
    page = template.replace("__TITLE__", title).replace("__NODES__", data)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project")
    parser.add_argument("--include", action="append", default=[])
    args = parser.parse_args()
    try:
        print(build(args.output, project=args.project, include=args.include))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
