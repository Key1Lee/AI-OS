"""Ingest the fictional Markdown policies through the authenticated admin API."""
import json
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
token = json.loads((root / "access-tokens.json").read_text())["admin"]
documents = [{"filename": p.name, "markdown": p.read_text()} for p in sorted((root / "policies").glob("*.md"))]
response = httpx.post("http://127.0.0.1:8810/admin/ingest", headers={"Authorization": "Bearer " + token}, json={"documents": documents}, timeout=180)
response.raise_for_status()
print(json.dumps(response.json(), indent=2))
