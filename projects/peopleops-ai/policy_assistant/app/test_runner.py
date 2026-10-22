"""Permission-gated serial subprocess jobs; no client commands or raw log responses."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from threading import Lock, Thread
from time import perf_counter
from uuid import uuid4
import xml.etree.ElementTree as ET

from evals.provenance import fingerprint

ROOT = Path(__file__).resolve().parents[1]
SUITES = ("unit", "integration", "security", "evaluations")


class JobError(Exception):
    def __init__(self, status_code, code):
        self.status_code, self.code = status_code, code
        super().__init__(code)


def read_results(directory):
    """Parse actual JUnit/coverage/evaluation files without exposing assertion payloads."""
    result = {"tests": None, "coverage_percent": None, "evaluations": None}
    junit = directory/"tests.xml"
    if junit.is_file():
        root = ET.parse(junit).getroot()
        cases = list(root.iter("testcase"))
        failures = [c for c in cases if c.find("failure") is not None or c.find("error") is not None]
        skipped = sum(c.find("skipped") is not None for c in cases)
        # Parameter text can contain fixture content; expose function IDs only.
        ids = sorted({c.attrib.get("classname", "")+"::"+c.attrib["name"].split("[")[0] for c in failures})
        result["tests"] = {"total": len(cases), "passed": len(cases)-len(failures)-skipped,
                           "failed": len(failures), "skipped": skipped, "failed_test_ids": ids}
    coverage = directory/"coverage.json"
    if coverage.is_file():
        result["coverage_percent"] = json.loads(coverage.read_text())["totals"]["percent_covered"]
    evaluation = directory/"evaluation.json"
    if evaluation.is_file():
        report = json.loads(evaluation.read_text())
        result["evaluations"] = {layer: {k: v for k, v in report[layer].items() if k != "cases"}
                                  for layer in ("routing", "retrieval", "grounding", "security")}
        result["evaluations"].update({"release": report["release"], "reliability": report["reliability"],
                                      "traceability": {k: v for k, v in report["traceability"].items() if k != "tests"}})
    return result


def stop_process(process):
    """Terminate only the owned worker process group on the supported local POSIX runtime."""
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
    else:
        process.kill()
    process.wait()


class TestJobRunner:
    __test__ = False

    def __init__(self, directory, timeout=120):
        self.directory, self.timeout = Path(directory), timeout
        self.lock, self.jobs, self.process, self.thread = Lock(), {}, None, None

    def _save(self, job):
        directory = self.directory/job["job_id"]
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory/"state.tmp"
        temporary.write_text(json.dumps(job, indent=2)+"\n")
        temporary.replace(directory/"state.json")

    def start(self, suite, tenant):
        """Accept only a fixed suite, with one active child and a bounded report inventory."""
        if suite not in SUITES:
            raise JobError(422, "unknown_suite")
        with self.lock:
            if any(j["status"] in ("queued", "running") for j in self.jobs.values()):
                raise JobError(409, "test_job_already_running")
            if self.directory.exists() and len(list(self.directory.glob("*/state.json"))) >= 40:
                raise JobError(429, "local_report_limit_reached")
            job = {"job_id": str(uuid4()), "suite": suite, "status": "queued", "tenant": tenant,
                   "started_utc": datetime.now(timezone.utc).isoformat(), "duration_ms": None,
                   "source_fingerprint": fingerprint(), "exit_code": None, "failure_code": None,
                   "tests": None, "coverage_percent": None, "evaluations": None}
            self.jobs[job["job_id"]] = job
            self._save(job)
            self.thread = Thread(target=self._run, args=(job,), daemon=True)
            self.thread.start()
        return self.get(job["job_id"], tenant)

    def _launch(self, directory):
        # No inherited provider keys, user shell config or arbitrary Python path.
        environment = {key: value for key, value in os.environ.items() if key in
                       ("PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR", "TMP", "TEMP")}
        environment.update({"HR_DATABASE_PATH": str(directory/"runtime.sqlite3"),
                            "HR_LAB_REPORTS_PATH": str(directory/"nested"),
                            "HR_TEST_REPORT_DIR": str(directory), "COVERAGE_FILE": str(directory/".coverage"),
                            "PYTHONDONTWRITEBYTECODE": "1"})
        output = (directory/"process.log").open("w")
        try:
            process = subprocess.Popen([sys.executable, "-m", "app.lab_worker", "--suite", self._active_suite,
                                        "--output", str(directory)], cwd=ROOT, env=environment,
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=os.name == "posix")
        finally:
            output.close()
        return process

    def _run(self, job):
        start = perf_counter()
        directory = self.directory/job["job_id"]
        try:
            job["status"] = "running"
            self._save(job)
            self._active_suite = job["suite"]
            self.process = self._launch(directory)
            try:
                job["exit_code"] = self.process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                stop_process(self.process)
                job["status"], job["failure_code"] = "timed_out", "worker_deadline_exceeded"
            job.update(read_results(directory))
            if job["status"] != "timed_out":
                clean_tests = job["tests"] is not None and job["tests"]["failed"] == 0
                clean_evaluations = job["evaluations"] is None or job["evaluations"]["release"]["passed"]
                job["status"] = "passed" if job["exit_code"] == 0 and clean_tests and clean_evaluations else "failed"
                if job["status"] == "failed":
                    job["failure_code"] = "test_or_evaluation_failed"
        except Exception:
            job["status"], job["failure_code"] = "failed", "worker_or_artifact_error"
        finally:
            job["duration_ms"] = round((perf_counter()-start)*1000, 3)
            job["source_changed_during_run"] = job["source_fingerprint"] != fingerprint()
            self._save(job)

    def get(self, job_id, tenant):
        if not re.fullmatch(r"[0-9a-f-]{36}", job_id):
            raise JobError(404, "test_job_not_found")
        path = self.directory/job_id/"state.json"
        if not path.is_file():
            raise JobError(404, "test_job_not_found")
        job = json.loads(path.read_text())
        if job["tenant"] != tenant:
            raise JobError(404, "test_job_not_found")
        job.pop("tenant")
        job["current_source"] = job["source_fingerprint"] == fingerprint() and not job.get("source_changed_during_run", False)
        return job

    def recent(self, tenant):
        if not self.directory.exists():
            return []
        paths = sorted(self.directory.glob("*/state.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:20]
        jobs = []
        for path in paths:
            try:
                jobs.append(self.get(path.parent.name, tenant))
            except JobError:
                continue
        return jobs

    def close(self):
        if self.process is not None:
            stop_process(self.process)
        if self.thread is not None:
            self.thread.join(timeout=2)
