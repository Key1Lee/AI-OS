import ast
import csv
import json
import yaml

from evals.common import ROOT, cases


def traceability_report():
    """Check actual test decorators, implementation paths and dataset links against the BRD."""
    requirements = yaml.safe_load((ROOT / "requirements/business_requirements.yaml").read_text())["requirements"]
    ids = {row["id"] for row in requirements}
    tests, unmapped, invalid = {}, [], []
    for directory in ("unit", "integration", "security", "end_to_end", "performance"):
        for path in (ROOT / "tests" / directory).glob("test_*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                    continue
                mapped = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "requirement":
                        mapped.extend(arg.value for arg in decorator.args if isinstance(arg, ast.Constant))
                tests[node.name] = {"file": str(path.relative_to(ROOT)), "requirements": mapped}
                if not mapped:
                    unmapped.append(node.name)
                invalid.extend(req for req in mapped if req not in ids)
    evaluation_cases = [case for layer in ("routing", "retrieval", "grounding", "security") for case in cases(layer)]
    evaluated = {req for case in evaluation_cases for req in case["requirements"]}
    rows = list(csv.DictReader((ROOT / "requirements/traceability.csv").open()))
    missing_primary = [row["test_function"] for row in rows if row["test_function"] not in tests]
    missing_files = [path for row in requirements for path in row["implementation"] if not (ROOT / path).is_file()]
    untested = sorted(ids - {req for item in tests.values() for req in item["requirements"]})
    report = {"requirements": len(ids), "test_functions": len(tests), "evaluation_cases": len(evaluation_cases),
              "requirements_without_tests": untested, "tests_without_requirements": unmapped,
              "requirements_without_evaluations": sorted(ids - evaluated), "missing_primary_tests": missing_primary,
              "unknown_requirement_references": sorted(set(invalid)), "missing_implementation_files": sorted(set(missing_files)), "tests": tests}
    report["passed"] = not any(report[key] for key in ("requirements_without_tests", "tests_without_requirements", "requirements_without_evaluations", "missing_primary_tests", "unknown_requirement_references", "missing_implementation_files"))
    return report


if __name__ == "__main__":
    result = traceability_report()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
