"""Bounded live failure drills against this demo's isolated Compose services.

Temporarily alters only the running web container's reference, restores the exact
tracked reference, and restarts only this project's n8n. Always restores in finally.
"""
import json
import subprocess
import time
from datetime import datetime, timezone
from integration import ROOT, BASE, request


def compose(*args):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def restore():
    compose("cp", "fixtures/golden_report.json", "web:/app/fixtures/golden_report.json")


def main():
    evidence = {"timestamp": datetime.now(timezone.utc).isoformat(), "checks": {}}
    try:
        compose("exec", "-T", "--user", "root", "web", "node", "-e", "const fs=require('node:fs');const p='/app/fixtures/golden_report.json';const g=JSON.parse(fs.readFileSync(p));for(const r of Object.values(g.reports)){r.overall.score+=10;}fs.writeFileSync(p,JSON.stringify(g));")
        status, failed = request(BASE + "/api/report")
        assert status == 409 and failed["validation"]["status"] == "FAIL" and failed["report"] is None
        status, chat = request(BASE + "/api/chat", {"question": "company survey score"})
        assert status == 409 and chat["validation"]["status"] == "FAIL" and chat["report"] is None, chat
        evidence["checks"]["corruptedReference"] = {"dashboard": failed, "chat": chat}
        print("PASS corrupt reference: report and actual n8n chat return FAIL with no numerical report.")
    finally:
        restore()
    try:
        compose("exec", "-T", "--user", "root", "web", "node", "-e", "require('node:fs').unlinkSync('/app/fixtures/golden_report.json')")
        status, unavailable = request(BASE + "/api/report")
        assert status == 409 and unavailable["validation"]["status"] == "NOT VERIFIED" and unavailable["report"] is None
        evidence["checks"]["missingReference"] = unavailable
        print("PASS missing reference: NOT VERIFIED with no numerical report.")
    finally:
        restore()
    try:
        compose("stop", "n8n")
        status, unavailable = request(BASE + "/api/chat", {"question": "company survey score"})
        assert status == 503 and unavailable["validation"]["status"] == "NOT VERIFIED", unavailable
        assert "No n8n execution" in unavailable["error"]
        evidence["checks"]["stoppedN8n"] = unavailable
        print("PASS stopped n8n: 503 and explicit no-execution message.")
    finally:
        compose("start", "n8n")
    for _ in range(60):
        try:
            status, recovery = request(BASE + "/api/chat", {"question": "company survey score"})
            if status == 200:
                break
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    else:
        raise AssertionError("n8n did not recover after restart")
    assert recovery["validation"]["status"] == "PASS"
    evidence["checks"]["recovered"] = {"status": recovery["validation"]["status"], "execution": recovery["orchestration"]}
    evidence["status"] = "PASS"
    (ROOT / "evidence/failure-probes.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS services and original reference restored; fresh webhook execution verified.")


if __name__ == "__main__":
    main()
