from datetime import date
import json
import os
from pathlib import Path
import shutil
import subprocess
from threading import Event

import pytest
from pydantic import ValidationError
import yaml

from app.diagnostics import ExecutionTrace
from app.intent_router import route_intent
from app.lab_worker import run_worker
from app.models import Intent
from app.rules import RuleBook, SecurityPolicies, default_rules
from app.test_runner import JobError, TestJobRunner, read_results, stop_process
from app.workday_client import RecordError, validate_record
from tests.unit.test_enterprise_units import document, principal

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.requirement("HR-005", "HR-014")
def test_yaml_routing_is_executable(tmp_path):
    directory = tmp_path/"config"
    shutil.copytree(ROOT/"config", directory)
    path = directory/"routing_rules.yaml"
    data = yaml.safe_load(path.read_text())
    data["rules"][4]["any_patterns"].append(r"\bfringe perk\b")
    path.write_text(yaml.safe_dump(data))
    assert route_intent("fringe perk", RuleBook(directory)).intent == Intent.POLICY_QUESTION
    assert route_intent("fringe perk").intent == Intent.AMBIGUOUS_REQUEST
    data["rules"].pop(0)
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValidationError, match="seven intent"):
        RuleBook(directory)


@pytest.mark.requirement("HR-004", "HR-015")
def test_yaml_security_cannot_disable_deny_default(tmp_path):
    raw = default_rules().security.model_dump()
    raw["deny_by_default"] = False
    with pytest.raises(ValidationError):
        SecurityPolicies.model_validate(raw)
    directory = tmp_path/"config"
    shutil.copytree(ROOT/"config", directory)
    path = directory/"business_rules.yaml"
    data = yaml.safe_load(path.read_text())
    data["rules"].append(data["rules"][0])
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="Duplicate"):
        RuleBook(directory)


@pytest.mark.requirement("HR-009", "HR-010")
def test_measured_trace_distinguishes_failed_and_unexecuted():
    trace = ExecutionTrace()
    with pytest.raises(RecordError):
        with trace.step("retrieval", ["BR-SOURCE-FRESH"]):
            raise RecordError("timeout")
    rows = trace.complete()
    assert rows[0].status == "failed" and rows[0].duration_ms >= 0
    assert all(row.duration_ms == 0 for row in rows if row.status == "skipped")
    assert {r.stage for r in rows} >= {"authentication", "retrieval", "validation", "response"}


@pytest.mark.requirement("HR-002", "HR-004", "HR-011")
def test_injected_record_contract_is_revalidated(enterprise_settings):
    record = {"employee_id":"EMP100", "tenant":"acme", "pto_balance":12.5, "unit":"days", "as_of_date":date(2026,10,20)}
    assert validate_record(record, principal(), "EMP100", enterprise_settings).pto_balance == 12.5
    for update, code in [({"pto_balance":-1}, "malformed"), ({"tenant":"other"}, "invalid_scope"), ({"as_of_date":date(2020,1,1)}, "stale")]:
        with pytest.raises(RecordError) as error:
            validate_record({**record, **update}, principal(), "EMP100", enterprise_settings)
        assert error.value.status == code


@pytest.mark.requirement("HR-006", "HR-013")
def test_document_content_alias_preserves_source():
    from app.models import Document
    raw = document().model_dump()
    raw["content"] = raw.pop("text")
    assert Document.model_validate(raw).text == raw["content"]


def artifacts(directory):
    (directory/"tests.xml").write_text('<testsuites><testsuite><testcase classname="tests.unit" name="test_pass"/><testcase classname="tests.unit" name="test_fail[PRIVATE_INPUT]"><failure>SECRET</failure></testcase><testcase classname="tests.unit" name="test_skip"><skipped/></testcase><testcase classname="tests.unit" name="test_error"><error>SECRET</error></testcase></testsuite></testsuites>')
    (directory/"coverage.json").write_text(json.dumps({"totals":{"percent_covered":88.5}}))


@pytest.mark.requirement("HR-009", "HR-012")
def test_real_artifact_parser_excludes_assertion_payloads(tmp_path):
    artifacts(tmp_path)
    result = read_results(tmp_path)
    assert result["tests"] == {"total":4,"passed":1,"failed":2,"skipped":1,"failed_test_ids":["tests.unit::test_error","tests.unit::test_fail"]}
    assert result["coverage_percent"] == 88.5
    assert "SECRET" not in json.dumps(result) and "PRIVATE_INPUT" not in json.dumps(result)
    report = {layer:{"passed":1,"total":1,"failed_case_ids":[],"cases":[{"secret":"hidden"}]} for layer in ("routing","retrieval","grounding","security")}
    report.update({"release":{"passed":True},"reliability":{"samples":1},"traceability":{"passed":True,"tests":{"private":"hidden"}}})
    (tmp_path/"evaluation.json").write_text(json.dumps(report))
    assert "hidden" not in json.dumps(read_results(tmp_path))


class CompletedProcess:
    pid = 424242
    def wait(self, timeout=None):
        return 0
    def poll(self):
        return 0


@pytest.mark.requirement("HR-010", "HR-012", "HR-015")
def test_job_lifecycle_serialization_and_tenant_scope(tmp_path, monkeypatch):
    runner = TestJobRunner(tmp_path)
    release = Event()
    class Process(CompletedProcess):
        def wait(self, timeout=None):
            release.wait(2)
            return 0
    def launch(directory):
        artifacts(directory)
        return Process()
    monkeypatch.setattr(runner, "_launch", launch)
    started = runner.start("unit", "acme")
    with pytest.raises(JobError) as error:
        runner.start("security", "acme")
    assert error.value.status_code == 409
    release.set()
    runner.thread.join(2)
    result = runner.get(started["job_id"], "acme")
    # Exit code 0 with a failing JUnit must never be reported as passed.
    assert result["tests"]["failed"] == 2 and result["status"] == "failed"
    assert result["current_source"]
    assert len(runner.recent("acme")) == 1 and runner.recent("other") == []
    with pytest.raises(JobError):
        runner.get(started["job_id"], "other")
    with pytest.raises(JobError):
        runner.get("../../private", "acme")
    with pytest.raises(JobError):
        runner.get("0"*36, "acme")
    runner.close()


@pytest.mark.requirement("HR-007", "HR-010", "HR-012")
@pytest.mark.parametrize("failure", ["deadline", "launch", "artifact"])
def test_worker_failures_are_safe(tmp_path, monkeypatch, failure):
    runner = TestJobRunner(tmp_path)
    class Deadline(CompletedProcess):
        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired("private command", timeout)
    def launch(directory):
        if failure == "launch":
            raise RuntimeError("PRIVATE_SOURCE_PAYLOAD")
        if failure == "artifact":
            (directory/"tests.xml").write_text("PRIVATE_BAD_XML")
        return Deadline() if failure == "deadline" else CompletedProcess()
    monkeypatch.setattr(runner, "_launch", launch)
    stopped = []
    monkeypatch.setattr("app.test_runner.stop_process", lambda process: stopped.append(True))
    started = runner.start("unit", "acme")
    runner.thread.join(2)
    result = runner.get(started["job_id"], "acme")
    assert result["status"] in ("failed", "timed_out") and result["failure_code"]
    assert "PRIVATE" not in json.dumps(result)
    assert bool(stopped) == (failure == "deadline")


@pytest.mark.requirement("HR-012", "HR-015")
def test_subprocess_command_and_environment_are_fixed(tmp_path, monkeypatch):
    runner = TestJobRunner(tmp_path)
    runner._active_suite = "unit"
    calls = []
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_API_KEY")
    monkeypatch.setenv("PYTHONPATH", "/untrusted")
    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess()
    monkeypatch.setattr("app.test_runner.subprocess.Popen", spawn)
    runner._launch(tmp_path)
    command, options = calls[0]
    assert command[1:5] == ["-m","app.lab_worker","--suite","unit"]
    assert "shell" not in options and options["cwd"] == ROOT
    assert "OPENAI_API_KEY" not in options["env"] and "PYTHONPATH" not in options["env"]
    assert options["env"]["HR_TEST_REPORT_DIR"] == str(tmp_path)
    with pytest.raises(JobError):
        runner.start("unit; echo private", "acme")
    for index in range(40):
        path = tmp_path/str(index)
        path.mkdir()
        (path/"state.json").write_text("{}")
    with pytest.raises(JobError) as error:
        runner.start("unit", "acme")
    assert error.value.status_code == 429


@pytest.mark.requirement("HR-010", "HR-012")
def test_owned_process_group_cleanup(monkeypatch):
    process = CompletedProcess()
    stop_process(process)
    calls = []
    monkeypatch.setattr(process, "poll", lambda: None)
    if os.name == "posix":
        monkeypatch.setattr("app.test_runner.os.killpg", lambda pid, sig: calls.append(pid))
        stop_process(process)
        assert calls == [process.pid]


@pytest.mark.requirement("HR-012", "HR-014")
@pytest.mark.parametrize("suite,status,expected_calls", [("unit",0,1),("evaluations",1,1),("evaluations",0,2)])
def test_worker_runs_pytest_before_evaluations(tmp_path, monkeypatch, suite, status, expected_calls):
    monkeypatch.setenv("HR_TEST_REPORT_DIR", os.environ.get("HR_TEST_REPORT_DIR",str(tmp_path)))
    monkeypatch.setenv("COVERAGE_FILE", os.environ.get("COVERAGE_FILE",str(tmp_path/".coverage")))
    calls = []
    monkeypatch.setattr("app.lab_worker.subprocess.call", lambda command, **kwargs: calls.append(command) or status)
    assert run_worker(suite, tmp_path) == status
    assert len(calls) == expected_calls and calls[0][1:3] == ["-m","pytest"]
    if expected_calls == 2:
        assert calls[1][1:3] == ["-m","evals.run_evaluations"]
