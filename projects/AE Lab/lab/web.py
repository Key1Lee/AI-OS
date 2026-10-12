"""Loopback-only browser learning surface over the existing Lab coordinator."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import mimetypes
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from uuid import UUID
import webbrowser

from .adapters.bridge import AdapterError, ROOT
from .contracts import State
from .core import Lab
from .learning import STEPS
from .store import StateError
from .warehouse import Warehouse
from .business import BusinessLab, business_view
from .business_catalog import CASES, VERSION

ASSETS = Path(__file__).with_name("web_assets")

def resume_step(record: dict) -> int:
    if record.get("kind") == VERSION:
        return record["learning_step"]
    step, state = record["learning_step"], record["state"]
    if state in {State.BASELINE, State.FAULT_INJECTED}:
        return 2
    if state == State.DIAGNOSING:
        diagnoses = record["answers"].get("diagnose", [])
        return 5 if diagnoses and diagnoses[-1]["evaluation"]["outcome"] == "pass" else 4
    if state == State.FAILED:
        return min(max(step, 3), 4)
    if state == State.REMEDIATED:
        return 6 if "recovery" in record["phases"] else 5
    if state == State.VERIFIED:
        if not record["verification"] or record["verification"]["status"] != "PASS":
            return 6
        return min(max(step, 7), 9)
    if state == State.MASTERED:
        return min(max(step, 8), 9)
    return step

def session_view(record: dict) -> dict:
    """Progressive disclosure: never return fault evidence or answers before observe."""
    if record.get("kind") == VERSION:
        return business_view(record)
    step = resume_step(record)
    result = {key: record[key] for key in ("run_id", "state", "created_at", "scenario_id", "assistance")}
    result["step"] = step
    result["evidence"] = {}
    if step >= 3:
        for name, phase in record["phases"].items():
            result["evidence"][name] = {key: phase[key] for key in (
                "rows", "expected_rows", "revenue", "expected_revenue", "duplicate_extra",
                "pipeline_status", "quality_status", "model_status", "publication", "freshness")}
            result["evidence"][name]["attempts"] = [
                {"attempt": a["native"]["attempt"], "status": a["native"]["status"], "rows": a["warehouse_rows_after_attempt"]}
                for a in phase["attempts"]]
            result["evidence"][name]["incidents"] = phase["observability"]["incidents"]
            result["evidence"][name]["impact"] = phase["observability"]["impact"]
    result["verification"] = record["verification"] if step >= 6 else None
    result["feedback"] = {}
    for stage, answers in record["answers"].items():
        if stage == "predict" and step < 3:
            continue
        if answers:
            evaluation = answers[-1]["evaluation"]
            result["feedback"][stage] = {key: evaluation[key] for key in ("outcome", "feedback", "score")}
    return result

class Application:
    def __init__(self, state_dir: Path):
        self.lab = Lab(state_dir)
        self.business = BusinessLab(self.lab.store)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lab-run")
        self.job = None

    def action(self, record: dict, action: str, answer: dict):
        if record.get("kind") == VERSION:
            return self.business.action(record, action, answer)
        run_id, step = record["run_id"], resume_step(record)
        expected = ["continue", "predict", "run", "continue", "diagnose", "fix", "verify", "recall", "continue"]
        if step >= 9 or action != expected[step]:
            raise StateError("This action belongs to a different exercise step. Reload the session.")
        if action in {"predict", "diagnose", "recall"}:
            evaluation = self.lab.answer(run_id, action, answer)
            if action != "predict" and evaluation["outcome"] != "pass":
                return session_view(self.lab.store.get(run_id))
        elif action == "run":
            self.lab.run(run_id)
        elif action == "fix":
            if answer.get("repair") not in {"upsert", "merge"}:
                raise StateError("Choose a write operation that can update an existing order by its stable key.")
            self.lab.fix(run_id)
        elif action == "verify":
            checked = self.lab.verify(run_id)
            if checked["verification"]["status"] != "PASS":
                raise StateError("Verification found a remaining problem. Review the evidence before continuing.")
        record = self.lab.store.get(run_id)
        record["learning_step"] = step + 1
        self.lab.save(record)
        return session_view(record)

    def submit(self, record, action, answer):
        if self.job and self.job["status"] == "running":
            raise StateError("An operation is already running. Wait for it to finish.")
        job = {"id": secrets.token_hex(12), "run_id": record["run_id"], "status": "running", "action": action}
        self.job = job
        def execute():
            try:
                result = self.action(record, action, answer)
                with self.lock:
                    job.update(status="done", result=result)
            except Exception as exc:
                with self.lock:
                    job.update(status="failed", error=str(exc))
        self.executor.submit(execute)
        return {key: job[key] for key in ("id", "run_id", "status", "action")}

class Handler(BaseHTTPRequestHandler):
    server_version = "AE-Lab/0.1"

    def log_message(self, *_args):
        pass

    @property
    def app(self):
        return self.server.app

    def send(self, status, body, content_type="application/json"):
        data = json.dumps(body).encode() if content_type == "application/json" else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def origin_ok(self):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return host in allowed and (origin is None or origin in {f"http://{h}" for h in allowed})

    def do_GET(self):
        if not self.origin_ok():
            self.send(403, {"error": "Open the Lab through its local browser address."})
            return
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                self.send(200, {"app": "ae-lab-browser-v1", "catalog_version": VERSION, "state_dir": str(self.app.lab.store.root)})
            elif path == "/api/catalog":
                self.send(200, {"cases": [{key:item[key] for key in ("id","number","title","sector","concept","priority")}
                                         for item in CASES]})
            elif path == "/api/bootstrap":
                with self.app.lock:
                    sessions = [{"run_id": r["run_id"], "state": r["state"], "created_at": r["created_at"], "scenario_id":r["scenario_id"],
                                 "step": resume_step(r), "demo": r["assistance"]["automated_demo"]}
                                for r in self.app.lab.store.records()]
                    job = {key: self.app.job[key] for key in ("id", "run_id", "status", "action")} if self.app.job else None
                    self.send(200, {"token": self.app.token, "sessions": sessions, "job": job})
            elif path.startswith("/api/sessions/"):
                run_id = path.split("/")[-1]
                UUID(run_id)
                self.send(200, session_view(self.app.lab.store.get(run_id)))
            elif path.startswith("/api/jobs/"):
                with self.app.lock:
                    if not self.app.job or self.app.job["id"] != path.split("/")[-1]:
                        raise StateError("Unknown operation")
                    self.send(200, self.app.job)
            elif path in {"/", "/index.html", "/app.js", "/business-app.js", "/style.css"}:
                file = ASSETS / ("index.html" if path == "/" else path[1:])
                self.send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "text/plain")
            else:
                self.send(404, {"error": "Page not found"})
        except (StateError, ValueError) as exc:
            self.send(404, {"error": str(exc)})

    def do_POST(self):
        if not self.origin_ok() or self.headers.get("X-Lab-Token") != self.app.token:
            self.send(403, {"error": "Reload the local Lab page before submitting an answer."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16000:
                raise ValueError("Answer is too large or empty")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected an answer object")
            path = urlparse(self.path).path
            with self.app.lock:
                if self.app.job and self.app.job["status"] == "running":
                    raise StateError("The Lab is working. Wait for the current operation to finish.")
                if path == "/api/sessions":
                    scenario_id=body.get("scenario_id")
                    if scenario_id is not None and not isinstance(scenario_id,str):
                        raise ValueError("Scenario ID must be a string")
                    record=self.app.lab.start() if scenario_id in {None,"ORCH-IDEMPOTENCY-001"} else self.app.business.start(scenario_id)
                    self.send(201, session_view(record))
                    return
                if path == "/api/actions":
                    record = self.app.lab.store.get(body.get("run_id", ""))
                    if type(body.get("step")) is not int or body["step"] != resume_step(record):
                        raise StateError("This page is out of date. Reload to resume the current step.")
                    answer = body.get("answer", {})
                    if not isinstance(answer, dict):
                        raise ValueError("Answer must be an object")
                    self.send(202, self.app.submit(record, body.get("action"), answer))
                    return
                self.send(404, {"error": "Unknown action"})
        except (StateError, ValueError, KeyError) as exc:
            self.send(409, {"error": str(exc)})

def create_server(state_dir: Path, port: int = 8088):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.app = Application(state_dir)
    return server

def main(argv=None):
    parser = argparse.ArgumentParser(description="Readable local Analytics Engineering Lab")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--state-dir", type=Path, default=Path(os.environ.get("AE_LAB_STATE_DIR", ROOT / ".lab")))
    parser.add_argument("--open", action="store_true", help="Open the local page in your browser")
    args = parser.parse_args(argv)
    try:
        server = create_server(args.state_dir, args.port)
    except OSError as exc:
        parser.exit(1, f"Cannot start the Lab on port {args.port}: {exc}\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Analytics Engineering Lab: {url}\nKeep this window open while learning. Press Control-C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.app.executor.shutdown(wait=True)

if __name__ == "__main__":
    main()
