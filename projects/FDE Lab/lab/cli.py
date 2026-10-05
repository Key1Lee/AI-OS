"""CLI and optional command shell; offline execution requires only Python."""
import argparse
import json
import shlex
import sys
from pathlib import Path

from .contracts import DIMENSIONS, load_scenario
from .engine import Engine, LabError, RUBRICS
from .store import Store

PROJECT = Path(__file__).resolve().parent.parent


def parser():
    p = argparse.ArgumentParser(prog="fde", description="Evidence-gated Forward Deployment Engineering Lab")
    p.add_argument("--state-dir", type=Path, default=PROJECT / "progress", help="Separate local learner state and workspace")
    sub = p.add_subparsers(dest="command")
    for command in ("next", "scenario", "stakeholders", "components", "progress", "map", "diagram",
                    "build", "break", "deploy", "recall", "hint", "solution", "reset", "log", "end", "integrations", "shell"):
        sub.add_parser(command)
    ask = sub.add_parser("ask", help="Interview a stakeholder about one specific topic")
    ask.add_argument("stakeholder")
    ask.add_argument("question", nargs="+")
    investigate = sub.add_parser("investigate")
    investigate.add_argument("question", nargs="+")
    evidence = sub.add_parser("evidence")
    evidence.add_argument("id", nargs="?")
    box = sub.add_parser("open")
    box.add_argument("component")
    for command in ("hypothesis", "frame", "requirements", "design", "evaluate", "harden", "debug", "measure", "explain", "answer"):
        submit = sub.add_parser(command, help=RUBRICS[command])
        submit.add_argument("reasoning", nargs="*")
        submit.add_argument("--file", type=Path, help="Read a learner-authored text/diagram artifact")
        submit.add_argument("--evidence", default="", help="Comma-separated released artifact or experiment event IDs")
        if command == "answer":
            submit.add_argument("--kind", choices=("answer", "recall"), default="answer")
    review = sub.add_parser("review", help="Tutor-only explicit assessment, recorded with attribution")
    review.add_argument("submission")
    review.add_argument("--result", choices=("developing", "demonstrated"), required=True)
    review.add_argument("--note", required=True)
    review.add_argument("--tutor", required=True, help="Name/identity of human or AI tutor who actually inspected the answer")
    review.add_argument("--concept", help="Optional concept ID to assess")
    review.add_argument("--dimension", choices=DIMENSIONS)
    test = sub.add_parser("test")
    test.add_argument("file", nargs="?", type=Path)
    return p


def execute(args):
    scenario = load_scenario()
    store = Store(args.state_dir)
    with store.locked():
        state = store.read(scenario) if args.command != 'reset' else None
        if args.command == 'reset':
            state = store.reset(scenario)
        engine = Engine(scenario, state, store.directory)
        command = args.command or "next"
        if command in {"next", "scenario", "reset"}:
            output = engine.next()
        elif command == "ask":
            output = engine.ask(args.stakeholder, " ".join(args.question))
        elif command == "investigate":
            output = engine.investigate(" ".join(args.question))
        elif command == "evidence":
            output = engine.evidence(args.id)
        elif command == "stakeholders":
            output = "\n".join(f"{key}: {person['name']} — {person['title']}" for key, person in scenario['stakeholders'].items())
        elif command == "components":
            output = "\n".join(f"{key}: {box['label']}" for key, box in scenario['components'].items())
        elif command == "open":
            output = engine.open(args.component)
        elif command == "diagram":
            output = engine.diagram()
        elif command in {"hypothesis", "frame", "requirements", "design", "evaluate", "harden", "debug", "measure", "explain", "answer"}:
            reasoning = args.file.read_text() if args.file else " ".join(args.reasoning)
            if not reasoning.strip():
                output = f"{command.upper()}\n{RUBRICS[command]}\n\nRecord your own reasoning and cite released evidence with --evidence."
            else:
                kind = args.kind if command == "answer" else command
                citations = [key.strip() for key in args.evidence.split(",") if key.strip()]
                output = engine.submit(kind, reasoning, citations)
        elif command == "review":
            output = engine.review(args.submission, args.result, args.note, args.concept, args.dimension, args.tutor)
        elif command == "test":
            output = engine.test(args.file)
        elif command == "integrations":
            source = PROJECT / "integrations" / "registry.json"
            if not source.exists():
                output = "Reference map is unavailable in this distribution. See the project docs/integrations.md."
            else:
                registry = json.loads(source.read_text())
                output = "Reference-only integration map; no sibling system is called.\n" + "\n".join(
                    f"{entry['name']}: {entry['relative_root']}" for entry in registry['systems'])
        else:
            methods = {"build": engine.build, "break": engine.break_system, "deploy": engine.deploy,
                       "recall": engine.recall, "progress": engine.progress, "map": engine.graph,
                       "hint": engine.hint, "solution": engine.solution, "log": engine.log, "end": engine.end}
            output = methods[command]()
        store.write(state)
        return output


def shell(args):
    args.command = "next"
    print(execute(args))
    while True:
        try:
            line = input("\nfde> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line in {"exit", "quit"}:
            return 0
        if not line:
            continue
        try:
            tokens = shlex.split(line)
            if tokens and tokens[0] == 'fde':
                tokens = tokens[1:]
            parsed = parser().parse_args(["--state-dir", str(args.state_dir), *tokens])
            if parsed.command == 'shell':
                print("You are already in the lab shell.")
                continue
            print(execute(parsed))
        except SystemExit:
            continue
        except (ValueError, OSError, KeyError) as error:
            print(f"Lab: {error}")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "shell":
            return shell(args)
        print(execute(args))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"Lab: {error}", file=sys.stderr)
        return 2
