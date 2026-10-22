"""Exercise the local production-checklist error path without any external messages."""

import json
import time
from pathlib import Path
from urllib.error import URLError

from .smoke import request


def main():
    """Cause one intentional n8n failure and wait for its local inbox notification."""
    inbox = "http://127.0.0.1:8812/notifications"
    before = {r["execution_id"] for r in request(inbox)["notifications"]}
    for attempt in range(10):
        try:
            request("http://127.0.0.1:5680/healthz")
            break
        except (URLError, OSError):
            if attempt == 9:
                raise
            time.sleep(1)
    request("http://127.0.0.1:5680/webhook/qualtrics-gold-failure-test", {})
    for _ in range(30):
        new = [
            r
            for r in request(inbox)["notifications"]
            if r["execution_id"] not in before
        ]
        if new:
            assert new[0]["workflow_id"] == "qualtricsGoldFailure01"
            assert new[0]["last_node"] == "Intentional checklist failure"
            break
        time.sleep(0.2)
    else:
        raise AssertionError(
            "Error workflow did not deliver a local notification within six seconds"
        )
    report = {
        "status": "passed",
        "probe": "intentional synthetic failure",
        "notification": new[0],
        "channel": "local_inbox",
        "external_messages_sent": 0,
    }
    (Path(__file__).parent / "reports/checklist-smoke.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
