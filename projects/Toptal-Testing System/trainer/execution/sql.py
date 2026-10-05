from __future__ import annotations

import json
import logging
import math
from importlib.metadata import version
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from threading import BoundedSemaphore
from time import monotonic

from trainer.config import Settings
from trainer.execution.compare import compare
from trainer.schemas.models import Exercise, TestCase

log = logging.getLogger(__name__)


class ExecutionUnavailable(RuntimeError):
    """Infrastructure failure: do not penalize learner evidence."""


class SqlRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.worker = Path(__file__).with_name("worker.py").resolve()
        self.capacity = BoundedSemaphore(2)

    @property
    def supported(self) -> bool:
        return sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").is_file()

    def _profile(self, temporary: Path) -> str:
        # No project-wide read grant: only the worker and installed runtime files.
        read_paths = [
            Path(sys.base_prefix), Path(sys.prefix) / "lib", self.worker,
            Path(sys.prefix) / "pyvenv.cfg", Path("/System/Library"),
            Path("/usr/lib"), Path("/Library/Apple/System/Library"),
        ]
        rules = " ".join(f'(subpath {json.dumps(str(p.resolve()))})' if p.is_dir() else f'(literal {json.dumps(str(p.resolve()))})' for p in read_paths)
        return f'''(version 1)
(deny default)
(allow process*)
(allow sysctl-read)
(allow mach-lookup)
(allow file-read-metadata)
(allow file-read* {rules} (literal "/") (literal "/dev/urandom") (literal "/dev/null") (literal "/dev/random"))
(allow file-read* file-write* (subpath {json.dumps(str(temporary.resolve()))}))
'''

    def execute(self, code: str, case: TestCase, *, timeout: float | None = None) -> dict:
        if not self.capacity.acquire(timeout=0.1):
            raise ExecutionUnavailable("The local SQL runner is busy. Your draft is saved; retry shortly.")
        try:
            return self._execute(code,case,timeout=timeout)
        finally:
            self.capacity.release()

    def _execute(self, code: str, case: TestCase, *, timeout: float | None = None) -> dict:
        if not self.supported:
            raise ExecutionUnavailable("SQL execution requires the macOS sandbox. Other hosts need an OS sandbox adapter; execution is disabled safely.")
        limit = min(timeout, self.settings.execution_timeout) if timeout is not None else self.settings.execution_timeout
        payload = {"code": code, "tables": [t.model_dump() for t in case.tables], "max_rows": self.settings.max_rows, "cpu_seconds": math.ceil(limit) + 1}
        started = monotonic()
        with tempfile.TemporaryDirectory(prefix="ae-sql-") as directory:
            temporary = Path(directory)
            profile = temporary / "worker.sb"
            profile.write_text(self._profile(temporary))
            env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(temporary), "PYTHONNOUSERSITE": "1", "OMP_NUM_THREADS": "1"}
            try:
                result = subprocess.run(
                    ["/usr/bin/sandbox-exec", "-f", str(profile), sys.executable, "-I", str(self.worker)],
                    input=json.dumps(payload), text=True, capture_output=True, cwd=temporary,
                    env=env, timeout=limit, check=False,
                )
            except subprocess.TimeoutExpired:
                return {"ok": False, "kind": "timeout", "error": "Execution time limit exceeded. Check join cardinality and query scope.", "duration_ms": int((monotonic() - started) * 1000)}
            if result.returncode != 0:
                log.error(json.dumps({"event": "sql_worker_failure", "exit_code": result.returncode}))
                raise ExecutionUnavailable("The isolated SQL worker could not start or complete. Your work is saved; no mastery change was recorded.")
            try:
                view = json.loads(result.stdout)
                if not isinstance(view, dict) or not isinstance(view.get("ok"), bool):
                    raise ValueError("Invalid worker output")
            except (ValueError, TypeError) as exc:
                raise ExecutionUnavailable("The SQL worker returned invalid output. Your work is saved.") from exc
        view["duration_ms"] = int((monotonic() - started) * 1000)
        return view

    def grade(self, code: str, exercise: Exercise) -> dict:
        categories = []
        started = monotonic()
        for index, case in enumerate([exercise.visible_case, *exercise.hidden_cases]):
            if monotonic() - started >= self.settings.suite_timeout:
                result = {"ok": False, "kind": "timeout", "error": "Test suite execution limit exceeded."}
            else:
                result = self.execute(code, case, timeout=self.settings.suite_timeout - (monotonic() - started))
            passed, reason = compare(result, exercise.expected_columns, case.expected_rows, ordered=exercise.ordered, tolerance=exercise.float_tolerance,expected_types=exercise.expected_types)
            feedback = case.diagnostic
            if reason == "output_schema":
                feedback = "Do the output column names, order and types match the published schema? " + ", ".join(f"{name}: {kind}" for name,kind in zip(exercise.expected_columns,exercise.expected_types))
            elif reason == "policy":
                feedback = "Is the submission a single read-only SELECT query? WITH is supported; changing data, files or configuration is disabled."
            elif reason == "timeout":
                feedback = "What drives the query's work? Check join fanout, filtering and repeated computation against the time limit."
            elif reason == "limit":
                feedback = "Does the result preserve the required grain and stay within the 1,000-row output limit?"
            categories.append({
                "id": case.id, "category": case.category, "passed": passed,
                "hidden": index > 0, "feedback": "Contract satisfied." if passed else feedback,
                "reason": reason, "competencies": case.competencies or exercise.competencies,
            })
        passed_count = sum(c["passed"] for c in categories)
        outcome = "Correct" if passed_count == len(categories) else "Partial" if passed_count else "Incorrect"
        return {"outcome": outcome, "passed": passed_count, "total": len(categories), "categories": categories, "duration_ms": int((monotonic() - started) * 1000),"execution_engine":"duckdb:"+version("duckdb"),"harness_version":"sql-v1","scoring_policy":"ae-v1"}
