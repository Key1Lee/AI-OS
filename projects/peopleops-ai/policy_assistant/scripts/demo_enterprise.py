"""Send signed synthetic Slack requests to the local enterprise reference API."""
import argparse
import json
import time
from uuid import uuid4
import httpx

from app.auth import slack_signature
from app.settings import HRSettings


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("question",nargs="?",default="How many PTO days do I have remaining?")
    parser.add_argument("--url",default="http://127.0.0.1:8811")
    args=parser.parse_args()
    settings=HRSettings.configured()
    event={"type":"event_callback","team_id":"T_DEMO","event_id":"EV_"+uuid4().hex,"event":{"type":"app_mention","user":"U100","text":args.question}}
    body=json.dumps(event,separators=(",",":")).encode()
    stamp=str(int(time.time()))
    signature=slack_signature(body,stamp,settings.slack_signing_secret.get_secret_value())
    response=httpx.post(args.url+"/slack/events",headers={"Authorization":"Bearer demo-employee-us","Content-Type":"application/json","X-Slack-Request-Timestamp":stamp,"X-Slack-Signature":signature},content=body,timeout=10)
    response.raise_for_status()
    print(json.dumps(response.json(),indent=2))


if __name__=="__main__":
    main()
