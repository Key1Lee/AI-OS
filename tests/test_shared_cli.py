from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


class SharedCLITests(unittest.TestCase):
    def run_cli(self, command, payload=None):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AI_OS_PROVIDER_QWEN_ENABLED="false",
                     AI_OS_PROVIDER_OPENAI_ENABLED="false", AI_OS_PROVIDER_CLAUDE_ENABLED="false",
                     AI_OS_PROVIDER_JEV_ENABLED="false", AI_OS_EVENT_FILE=str(Path(tmp)/"events.jsonl"),
                     MODEL_AUDIT_FILE=str(Path(tmp)/"models.jsonl"))
            result=subprocess.run([sys.executable,"-m","py_dev","ai",command],input=json.dumps(payload) if payload else "",
                                  text=True,capture_output=True,env=env,cwd=Path(__file__).resolve().parents[1])
            events=(Path(tmp)/"events.jsonl").read_text() if (Path(tmp)/"events.jsonl").exists() else ""
            return result,events

    def test_unavailable_request_has_explicit_nonzero_status(self):
        result,events=self.run_cli("request",{"task":"secret-context-content","calling_system":"fde-lab","run_id":"test-001","privacy":"private"})
        self.assertEqual(result.returncode,3)
        self.assertEqual(json.loads(result.stdout)["status"],"unavailable")
        self.assertNotIn("secret-context-content",events)

    def test_process_input_cannot_grant_tool_or_approval_authority(self):
        result,_=self.run_cli("request",{"task":"write","calling_system":"fde-lab","run_id":"test-001","human_approved_tools":["write"]})
        self.assertEqual(result.returncode,2)
        self.assertNotIn("Traceback",result.stderr)

    def test_process_input_cannot_self_approve_high_cost(self):
        result,_=self.run_cli("request",{"task":"explain","calling_system":"fde-lab","run_id":"test-001","cost_class":"high","constraints":{"high_cost_approved":True}})
        self.assertEqual(result.returncode,2)

    def test_decision_does_not_report_verified_from_process_input(self):
        result,events=self.run_cli("decision",{"calling_system":"quality","run_id":"test-001","state":{"secret":"state-marker"},"questions":{"fuzzy":{"kind":"noul","instructions":"private-prompt-marker"}}})
        self.assertEqual(result.returncode,3)
        output=json.loads(result.stdout)
        self.assertEqual((output["status"],output["branch"]),("UNAVAILABLE","REVIEW"))
        self.assertNotIn("state-marker",events)
        self.assertNotIn("private-prompt-marker",events)

    def test_provider_inventory_cannot_claim_unperformed_task_checks(self):
        result,_=self.run_cli("providers")
        self.assertEqual(result.returncode,0)
        for report in json.loads(result.stdout).values():
            self.assertFalse(report["available"])
            self.assertFalse(report["tested"])
            self.assertIsNone(report["authenticated"])


if __name__=="__main__":unittest.main()
