"""Generate local credentials without replacing an existing configuration."""
import hashlib
import json
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
if (root / ".env").exists() or (root / "access-tokens.json").exists():
    raise SystemExit("Configuration already exists; preserved it. Edit .env deliberately to change settings.")
credentials, tokens = [], {}
for name, region, role in [("employee-us", "US", "employee"), ("employee-gb", "GB", "employee"), ("hr-us", "US", "hr"), ("admin", "US", "admin")]:
    token = secrets.token_urlsafe(32)
    tokens[name] = token
    credentials.append({"token_sha256": hashlib.sha256(token.encode()).hexdigest(), "identity": {"subject": name, "tenant": "fictional-acme", "region": region, "role": role}})
password = secrets.token_hex(24)
template = (root / ".env.example").read_text()
template = template.replace("replace-with-a-random-local-password", password)
template = template.replace("replace-with-a-random-local-encryption-key", secrets.token_hex(32))
template = template.replace("AUTH_CREDENTIALS=[]", "AUTH_CREDENTIALS='" + json.dumps(credentials, separators=(",", ":")) + "'")
for name, content in [(".env", template), ("access-tokens.json", json.dumps(tokens, indent=2) + "\n")]:
    path = root / name
    with path.open("x") as file:
        path.chmod(0o600)
        file.write(content)
print("Created .env and access-tokens.json with owner-only permissions. No paid provider is enabled.")
