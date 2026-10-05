#!/usr/bin/env python3
"""Execute real dbt in isolated copies; prove healthy and deliberately bad inputs."""
from __future__ import annotations

import csv
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from quality_system.adapters import dbt_export, dbt_result
from quality_system.engine import compile_contract
from quality_system.scenarios import BASE_CLOCK, data_contract

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/test-results"
EVIDENCE.mkdir(parents=True, exist_ok=True)
DBT = Path(sys.executable).parent / "dbt"
if not DBT.exists():
    raise SystemExit("Install the optional runtime: uv sync --extra dev --extra dbt")


def run(command, directory, case):
    env = {**os.environ, "DBT_SEND_ANONYMOUS_USAGE_STATS": "false", "DO_NOT_TRACK": "1",
           "QUALITY_DBT_DATABASE": str(directory / "lab.duckdb")}
    result = subprocess.run([str(DBT), *command, "--project-dir", str(directory), "--profiles-dir", str(directory),
                            "--no-use-colors"], env=env, text=True, capture_output=True, timeout=120)
    EVIDENCE.joinpath(f"dbt-{case}-{command[0]}.log").write_text(result.stdout + result.stderr)
    return result


evidence = {"runtime": {"dbt-core": version("dbt-core"), "dbt-duckdb": version("dbt-duckdb")}, "cases": []}
contract = data_contract()
rules = {r.id: r for r in compile_contract(contract)}
for case in ["valid", "duplicate", "unpaid", "schema", "unit_logic"]:
    with tempfile.TemporaryDirectory(prefix="quality-dbt-") as tmp:
        directory = Path(tmp)
        shutil.copytree(ROOT / "dbt_lab", directory, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("target", "logs", "*.duckdb*"))
        # Keep a single fct_orders YAML definition, merging native examples into generated contract.
        import yaml
        generated = dbt_export(contract)["document"]
        learning = yaml.safe_load((directory / "models/learning.yml").read_text())
        native = next(m for m in learning["models"] if m["name"] == "fct_orders")
        for extra in native["columns"]:
            next(c for c in generated["models"][0]["columns"] if c["name"] == extra["name"])["data_tests"] += extra["data_tests"]
        learning["models"] = [m for m in learning["models"] if m["name"] != "fct_orders"] + generated["models"]
        (directory / "models/learning.yml").write_text(yaml.safe_dump(learning, sort_keys=False))
        if case in {"duplicate", "unpaid"}:
            path = directory / "seeds/fct_orders_input.csv"
            with path.open() as file:
                reader = csv.DictReader(file); fields = reader.fieldnames; rows = list(reader)
            if case == "duplicate": rows.append(dict(rows[6]))
            else: rows[6]["payment_status"] = "unpaid"
            with path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fields); writer.writeheader(); writer.writerows(rows)
        if case == "schema":
            path = directory / "models/fct_orders.sql"
            path.write_text(path.read_text().replace("    cast(ordered_at as timestamptz) as ordered_at,\n", ""))
        if case == "unit_logic":
            path = directory / "models/completed_amount.sql"
            path.write_text("select sum(amount) as revenue from {{ ref('unit_orders') }}\n")
        seeded = run(["seed", "--full-refresh"], directory, case)
        if seeded.returncode:
            raise SystemExit(f"dbt seed failed for {case}; inspect docs/test-results/dbt-{case}-seed.log")
        built = run(["build", "--full-refresh"], directory, case)
        results_path = directory / "target/run_results.json"
        artifact = json.loads(results_path.read_text()) if results_path.exists() else {}
        manifest = json.loads((directory / "target/manifest.json").read_text())
        results = artifact.get("results", [])
        statuses = {r["unique_id"]: r["status"] for r in results}
        facts = [{"unique_id": r["unique_id"], "status": r["status"], "failures": r.get("failures")} for r in results]
        if case == "valid":
            assert built.returncode == 0 and results and all(r["status"] in {"pass", "success"} for r in results), facts
            assert any(k.startswith("unit_test.") and v == "pass" for k, v in statuses.items())
            assert manifest["nodes"]["model.quality_contracts_lab.fct_orders"]["contract"]["enforced"] is True
            assert any("source_unique" in k for k in statuses)
            assert any("relationships" in k for k in statuses)
            assert any("quality_unique_key" in k for k in statuses)
            # Preserve the positive runtime artifacts for consumer inspection.
            for name in ["manifest.json", "run_results.json"]:
                ROOT.joinpath("dbt_lab/target").mkdir(exist_ok=True)
                shutil.copy2(directory / "target" / name, ROOT / "dbt_lab/target" / name)
            mapped=[]
            for raw in results:
                node=manifest.get("nodes",{}).get(raw["unique_id"],{})
                rule_id=node.get("meta",{}).get("quality_rule_id") or node.get("config",{}).get("meta",{}).get("quality_rule_id")
                if rule_id in rules:
                    mapped.append(dbt_result(rules[rule_id],{**raw,"quality_rule_id":rule_id},BASE_CLOCK,"dbt-valid","recorded-dbt-artifact").model_dump(mode="json"))
            assert mapped and all(r["status"] == "PASS" for r in mapped)
            EVIDENCE.joinpath("dbt-normalized-results.json").write_text(json.dumps(mapped,indent=2)+"\n")
        elif case == "duplicate":
            assert built.returncode != 0 and any("quality_unique_key" in k and v == "fail" for k,v in statuses.items()), facts
        elif case == "unpaid":
            assert built.returncode != 0 and any("completed_is_paid" in k and v == "fail" for k,v in statuses.items()), facts
        elif case == "schema":
            assert built.returncode != 0 and statuses.get("model.quality_contracts_lab.fct_orders") == "error", facts
        else:
            assert built.returncode != 0 and any(k.startswith("unit_test.") and v == "fail" for k,v in statuses.items()), facts
        evidence["cases"].append({"case":case,"expected_failure":case!="valid","exit_code":built.returncode,"results":facts})
        print(f"{case}: expected behavior proven ({len(results)} dbt resources)", flush=True)
EVIDENCE.joinpath("dbt.json").write_text(json.dumps(evidence,indent=2)+"\n")
print("PASS: real dbt contracts, source/model data tests, custom/singular tests, native unit tests and four negative controls.")
