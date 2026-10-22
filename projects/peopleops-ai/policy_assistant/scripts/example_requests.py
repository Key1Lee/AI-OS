"""Exercise /ask or /chat without printing local credentials."""
import argparse
import json
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("question", nargs="?", default="How do I request PTO?")
parser.add_argument("--identity", choices=["employee-us", "employee-gb", "hr-us", "admin"], default="employee-us")
parser.add_argument("--via", choices=["ask", "chat", "webhook"], default="ask")
args = parser.parse_args()
tokens = json.loads((Path(__file__).resolve().parents[1] / "access-tokens.json").read_text())
url = "http://127.0.0.1:5680/webhook/peopleops-policy" if args.via == "webhook" else "http://127.0.0.1:8810/" + args.via
response = httpx.post(url, headers={"Authorization": "Bearer " + tokens[args.identity]}, json={"question": args.question}, timeout=60)
response.raise_for_status()
print(json.dumps(response.json(), indent=2))
