import json
from app.models import Principal
from app.mock_store import transaction


class MockIdentityProvider:
    """Resolve synthetic enterprise sessions; untrusted request fields never define roles."""

    def __init__(self, path, enabled=True):
        self.entries = json.loads(path.read_text()) if enabled else []

    def credential_entries(self):
        return [(entry["token_sha256"], Principal.model_validate(entry["principal"])) for entry in self.entries]

    def bind_slack(self, principal, team_id, user_id):
        """Require the signed Slack user and workspace to match the enterprise session."""
        return principal.team_id == team_id and principal.slack_user_id == user_id

    def demo_identities(self):
        return [{"label": entry["label"], "token": entry["demo_token"]} for entry in self.entries]


class SQLiteIdentityProvider(MockIdentityProvider):
    """Use the seeded mock database as runtime identity authority; JSON is only a seed."""
    def __init__(self, settings):
        self.database_path, self.enabled = settings.database_path, settings.demo_mode

    @property
    def entries(self):
        if not self.enabled:
            return []
        with transaction(self.database_path) as conn:
            return [json.loads(row[0]) for row in conn.execute("SELECT entry FROM mock_employees ORDER BY rowid")]
