from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .adapters.bridge import AdapterError, PROJECTS, ROOT, project_path
from .contracts import SCENARIO_ID, State
from .core import Lab
from .learning import CONNECT, DIAGNOSE, ORIENT, PREDICT, RECALL
from .store import StateError
from .telemetry import mermaid

def summary(record: dict):
    phase = record["phases"].get("rerun") or record["phases"].get("recovery") or record["phases"].get("fault")
    print(f"Run: {record['run_id']}\nState: {record['state']}")
    if phase:
        print(f"Expected rows: {phase['expected_rows']:,}\nActual rows:   {phase['rows']:,}\nDuplicate extra rows: {phase['duplicate_extra']:,}")
        print(f"Pipeline: {phase['pipeline_status']} | Modeling: {phase['model_status']} | Quality: {phase['quality_status']}\nFreshness: {phase['freshness']}")
        print(f"Revenue USD: {phase['revenue']} (expected {phase['expected_revenue']})\nPublication: {phase['publication']}")
        if phase["observability"]["impact"]:
            print("Downstream impact: " + ", ".join(phase["observability"]["impact"]))
    if record["verification"]:
        print("Verification: " + record["verification"]["status"])
        for criterion, passed in record["verification"]["checks"].items():
            print(f"  {'PASS' if passed else 'FAIL'} {criterion}")

def scenario(value: str):
    if value != SCENARIO_ID:
        raise ValueError(f"Unknown scenario {value}; use {SCENARIO_ID}")

def integer(prompt: str) -> int:
    while True:
        value = input(prompt).strip()
        try:
            return int(value.replace(",", ""))
        except ValueError:
            print("Enter a whole row count.")

def learn(lab: Lab, scenario_id: str, run_id: str | None = None):
    scenario(scenario_id)
    record = lab.store.get(run_id) if run_id else lab.start()
    if record["state"] == State.MASTERED and record["verification"] and record["verification"]["status"] == "PASS":
        if record["learning_step"] >= 9:
            print("This local exercise is complete. Use reset for a new isolated repetition.")
            return record
        record["learning_step"] = max(8, record["learning_step"])
    # Resuming manually executed phases does not repeat prediction after seeing evidence.
    if record["state"] in {State.FAILED, State.DIAGNOSING}:
        record["learning_step"] = max(3, record["learning_step"])
    elif record["state"] in {State.BASELINE, State.FAULT_INJECTED}:
        record["learning_step"] = 2
    elif record["state"] == State.REMEDIATED:
        record["learning_step"] = 6 if "recovery" in record["phases"] else 5
    elif record["state"] == State.VERIFIED:
        record["learning_step"] = max(7, record["learning_step"]) if record["verification"] and record["verification"]["status"] == "PASS" else 6
    while record["learning_step"] < 9:
        step = record["learning_step"]
        if step == 0:
            print("1 · ORIENT\n" + ORIENT)
            print("```mermaid\n" + mermaid("healthy", "fct_orders") + "\n```")
        elif step == 1:
            print("2 · PREDICT\n" + PREDICT)
            answer = {"rows": integer("Your predicted row count: ")}
            lab.answer(record["run_id"], "predict", answer)
            # Observe actual results before feedback; prediction is never a correctness gate.
        elif step == 2:
            print("3 · RUN — deterministic crash, then native retry")
            record = lab.run(record["run_id"])
        elif step == 3:
            print("4 · OBSERVE")
            summary(record)
            print(f"Evidence: {lab.directory(record) / 'evidence.json'}")
        elif step == 4:
            print("5 · DIAGNOSE\n" + DIAGNOSE)
            answer = {"layer": input("Layer: ").strip(), "property": input("Missing property: ").strip(),
                      "signal": input("Quality signal: ").strip(), "reason": input("Evidence in your own words: ").strip()}
            evaluation = lab.answer(record["run_id"], "diagnose", answer)
            print(evaluation["feedback"])
            if evaluation["outcome"] != "pass":
                record = lab.store.get(record["run_id"])
                continue
        elif step == 5:
            print("6 · FIX — choose the repaired write policy")
            choice = input("Write operation (append / upsert): ").strip().lower()
            if choice not in {"upsert", "merge"}:
                print("Append preserves the duplicate writes. Choose a policy that uses the stable order key.")
                continue
            record = lab.fix(record["run_id"])
            summary(record)
        elif step == 6:
            print("7 · VERIFY — compare every row, retry after another partial write, and repeat the load")
            record = lab.verify(record["run_id"])
            summary(record)
            if record["verification"]["status"] != "PASS":
                raise RuntimeError("Recovery verification failed; recall cannot proceed")
        elif step == 7:
            print("8 · RECALL\n" + RECALL)
            answer = {"rows": integer("Rows after another rerun: "), "key": input("Stable field: ").strip(),
                      "repair": input("Write operation: ").strip()}
            evaluation = lab.answer(record["run_id"], "recall", answer)
            print(evaluation["feedback"])
            if evaluation["outcome"] != "pass":
                record = lab.store.get(record["run_id"])
                continue
        elif step == 8:
            print("9 · CONNECT\n" + CONNECT)
            print("```mermaid\n" + mermaid("recovered") + "\n```")
        record = lab.store.get(record["run_id"])
        record["learning_step"] = step + 1
        lab.save(record)
    return record

def parser():
    p = argparse.ArgumentParser(prog="lab", description="See, break, diagnose, repair and recall one analytics pipeline.")
    p.add_argument("--state-dir", type=Path, default=Path(os.environ.get("AE_LAB_STATE_DIR", ROOT / ".lab")))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("systems")
    sub.add_parser("scenarios")
    for command in ("run", "learn", "reset"):
        item = sub.add_parser(command)
        item.add_argument("scenario_id")
        if command != "reset":
            item.add_argument("--resume", dest="run_id")
        if command == "run":
            item.add_argument("--seed", type=int, default=42)
            item.add_argument("--fail-after-rows", type=int, default=int(os.environ.get("FAIL_AFTER_ROWS", "700")))
    for command in ("inspect", "diagnose", "fix", "verify"):
        item = sub.add_parser(command)
        item.add_argument("run_id")
        if command == "inspect":
            item.add_argument("--json", action="store_true")
        if command == "diagnose":
            item.add_argument("--layer", required=True)
            item.add_argument("--property", required=True)
            item.add_argument("--signal", required=True)
            item.add_argument("--reason", default="")
    item = sub.add_parser("lineage")
    item.add_argument("asset")
    item.add_argument("--mode", choices=["healthy", "failed", "recovered"], default="healthy")
    sub.add_parser("progress")
    sub.add_parser("demo")
    return p

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "systems":
            for system, name in PROJECTS.items():
                path = project_path(system)
                runtime = path / "node_modules/.bin/tsx" if system == "orchestration" else Path(os.environ.get(f"AE_LAB_{system.upper()}_PYTHON", path / ".venv/bin/python"))
                print(f"{system}: {name}\n  {path}\n  runtime: {'available' if runtime.is_file() else 'MISSING'} ({runtime})")
            print(f"Inventory: {ROOT / 'docs/system-inventory.md'}")
            return 0
        if args.command == "scenarios":
            print(f"{SCENARIO_ID} | MUST KNOW | Partial write + retry | 1,000 → 1,700 → 1,000")
            return 0
        if args.command == "lineage":
            print(mermaid(args.mode, args.asset))
            return 0
        lab = Lab(args.state_dir)
        if args.command in {"run", "learn", "reset"}:
            scenario(args.scenario_id)
        if args.command == "run":
            record = lab.run(args.run_id, seed=args.seed, fail_after_rows=args.fail_after_rows)
            summary(record)
            print("Your task: identify the failing write property using the quality and retry evidence.")
        elif args.command == "learn":
            record = learn(lab, args.scenario_id, args.run_id)
        elif args.command == "reset":
            record = lab.reset(args.scenario_id)
            summary(record)
        elif args.command == "inspect":
            record = lab.store.get(args.run_id)
            print(json.dumps(record, indent=2)) if args.json else summary(record)
        elif args.command == "diagnose":
            evaluation = lab.answer(args.run_id, "diagnose", {"layer": args.layer, "property": args.property,
                                   "signal": args.signal, "reason": args.reason})
            print(evaluation["feedback"])
            return 0 if evaluation["outcome"] == "pass" else 1
        elif args.command == "fix":
            record = lab.fix(args.run_id)
            summary(record)
        elif args.command == "verify":
            record = lab.verify(args.run_id)
            summary(record)
            if record["verification"]["status"] != "PASS":
                return 1
        elif args.command == "progress":
            for record in lab.store.records():
                print(f"{record['run_id']} | {record['scenario_id']} | {record['state']} | step {record['learning_step']}/9")
            return 0
        elif args.command == "demo":
            record = lab.run()
            record["assistance"]["automated_demo"] = True
            lab.save(record)
            print("Automated architecture demonstration; learner mastery is not awarded.\nFAULT")
            summary(record)
            lab.answer(record["run_id"], "diagnose", {"layer": "ingestion", "property": "idempotency", "signal": "duplicate_order_ids",
                       "reason": "Automated demo answer; no learner evidence"})
            lab.fix(record["run_id"])
            record = lab.verify(record["run_id"])
            print("\nRECOVERY + REPEATED PARTIAL-WRITE RETRY")
            summary(record)
            print("\n" + RECALL)
            if record["verification"]["status"] != "PASS":
                return 1
        print(f"Saved evidence: {lab.directory(record) / 'evidence.json'}")
        return 0
    except (AdapterError, StateError, ValueError, RuntimeError, OSError) as exc:
        print(f"Lab stopped: {exc}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nSession saved. Resume with lab learn ORCH-IDEMPOTENCY-001 --resume RUN_ID; use lab progress to find the run.", file=sys.stderr)
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
