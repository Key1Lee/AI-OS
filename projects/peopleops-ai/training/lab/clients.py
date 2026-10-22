"""Single HTTP call only. Pagination, retries, and validation belong to E11."""
import httpx
from lab.config import Settings


class MockClient:
    def __init__(self, base_url=None, transport=None):
        self.client = httpx.Client(base_url=base_url or Settings().mock_url, timeout=0.2, transport=transport)

    def page(self, source, cursor=0, scenario="normal", attempt=1):
        response = self.client.get(f"/mock/{source}", params={"cursor": cursor, "scenario": scenario, "attempt": attempt})
        response.raise_for_status()
        return response.json()

    def close(self):
        self.client.close()
