from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path

from adapters.artifacts import artifact_export
from .core import DATA, Registry, SemanticError, evaluate, explain, lineage, load_catalog, load_snapshot, read_json
from .scenario import Scenario


def emit(value):
    print(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sem", description="Governed synthetic commerce semantics; no warehouse or AI client")
    parser.add_argument("--catalog", type=Path, help="Explicit alternate exported semantic catalog")
    parser.add_argument("--snapshot", type=Path, help="Explicit already-modeled synthetic snapshot")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("entities", "dimensions", "measures", "metrics", "validate", "test"):
        sub.add_parser(name)
    for name in ("show", "lineage", "explain"):
        p = sub.add_parser(name)
        p.add_argument("metric_id")
        p.add_argument("--version")
    p = sub.add_parser("concept")
    p.add_argument("name")
    p.add_argument("--step", choices=("orient", "fix", "recall"), default="orient")
    p = sub.add_parser("compare")
    p.add_argument("left")
    p.add_argument("right")
    p.add_argument("--version", default="1.0.0")
    p = sub.add_parser("query")
    p.add_argument("metric_id")
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--consumer", choices=("dashboard_a", "dashboard_b", "api", "ai", "sql"), default="api")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True, help="Exclusive reporting date")
    p.add_argument("--dimensions", nargs="*", default=[])
    p = sub.add_parser("export")
    p.add_argument("target", choices=("modeling", "quality", "observability", "ae-lab", "fde-lab"))
    p.add_argument("--metric", default="net_revenue")
    p.add_argument("--version", default="1.0.0")
    p = sub.add_parser("scenario")
    p.add_argument("scenario_id", choices=("SEM-REVENUE-001",))
    p.add_argument("action", nargs="?", choices=("predict", "inspect", "diagnose", "template", "propose", "apply", "verify", "recall", "status"))
    p.add_argument("--text")
    p.add_argument("--artifact")
    p.add_argument("--contract", type=Path)
    p.add_argument("--state-dir", type=Path, default=Path(__file__).resolve().parent.parent / "state")
    args = parser.parse_args(argv)
    try:
        if args.command == "test":
            tests = Path(__file__).resolve().parent.parent / "tests"
            if not (tests / "test_semantics.py").is_file():
                raise SemanticError("Run sem test from the source checkout; the installed runtime does not bundle test fixtures")
            suite = unittest.defaultTestLoader.discover(str(tests))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if result.wasSuccessful() else 1
        if args.command == "scenario":
            scenario = Scenario(args.state_dir)
            if args.action is None:
                emit(scenario.opening())
            elif args.action in {"predict", "diagnose"}:
                if args.text is None:
                    raise SemanticError("Use --text to record learner reasoning")
                emit(getattr(scenario, args.action)(args.text))
            elif args.action == "inspect":
                if args.artifact is None:
                    raise SemanticError("Choose one --artifact")
                emit(scenario.inspect(args.artifact))
            elif args.action == "template":
                emit(scenario.template())
            elif args.action == "propose":
                if args.contract is None:
                    raise SemanticError("Provide --contract with your proposed JSON definition")
                emit(scenario.propose(read_json(args.contract)))
            elif args.action == "status":
                emit({"stage": scenario.state["stage"], "inspected": scenario.state["inspected"], "assessment": scenario.state["assessment"], "recall_recorded": scenario.state["recall_answers"] is not None})
            else:
                emit(getattr(scenario, args.action)(args.text) if args.action == "recall" else getattr(scenario, args.action)())
            return 0
        if args.command == "concept":
            concepts = read_json(DATA / "concepts.json")
            if args.name not in concepts:
                raise SemanticError("Choose one concept: " + ", ".join(concepts))
            concept = concepts[args.name]
            if args.step == "orient":
                emit({key: concept[key] for key in ("concept", "diagram", "business_example", "failure", "question")})
            else:
                emit({"concept": concept["concept"], args.step: concept[args.step]})
            return 0
        registry = Registry(read_json(args.catalog) if args.catalog else None)
        snapshot = read_json(args.snapshot) if args.snapshot else load_snapshot()
        if args.command in {"entities", "dimensions", "measures", "metrics"}:
            emit(registry.catalog[args.command])
        elif args.command == "validate":
            emit(registry.validate())
        elif args.command == "show":
            emit(registry.get(args.metric_id, args.version))
        elif args.command == "lineage":
            emit(lineage(registry, args.metric_id, args.version))
        elif args.command == "explain":
            emit(explain(registry, args.metric_id, args.version))
        elif args.command == "compare":
            left, right = registry.get(args.left, args.version), registry.get(args.right, args.version)
            emit({"left": args.left, "right": args.right, "differences": {key: {"left": left[key], "right": right[key]} for key in left if left[key] != right[key]}, "question": "Which decision uses each metric, and who owns its meaning? A larger or smaller value does not decide correctness."})
        elif args.command == "query":
            emit(evaluate(registry, snapshot, {"contract_version": "semantic-query-v1", "metric_id": args.metric_id, "version": args.version, "consumer": args.consumer, "start": args.start, "end": args.end, "dimensions": args.dimensions}))
        elif args.command == "export":
            emit(artifact_export(args.target, registry, args.metric, args.version))
        return 0
    except (SemanticError, OSError, KeyError, TypeError) as exc:
        print("sem: " + str(exc), file=sys.stderr)
        return 2
