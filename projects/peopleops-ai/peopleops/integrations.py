"""HTTP request/retry practice through HTTPX MockTransport: zero real network I/O."""
from datetime import date, datetime, timedelta
import json
import time
import httpx
from .config import PACKAGE, Settings

ANCHOR = date(2026, 10, 17)
SCENARIOS = {"normal", "transient", "unavailable", "stale", "new_hire", "duplicate", "growth", "malformed"}


def source_records(settings: Settings, scenario="normal", volume=5000) -> list[dict]:
    records = json.loads((PACKAGE / "fixtures" / "employees.json").read_text())
    delta = settings.as_of - ANCHOR
    for record in records:
        for key in ("hire_date", "termination_date"):
            value = record[key]
            if not value:
                continue
            try:
                parsed = date.fromisoformat(value) if "-" in value else datetime.strptime(value, "%m/%d/%Y").date()
                shifted = parsed + delta
                record[key] = shifted.isoformat() if "-" in value else shifted.strftime("%m/%d/%Y")
            except ValueError:
                pass  # Deliberately invalid fixture remains invalid for quarantine.
        record["source_updated_at"] = (datetime.fromisoformat(record["source_updated_at"]) + delta).isoformat()
    if scenario == "stale":
        for record in records:
            record["source_updated_at"] = (datetime.fromisoformat(record["source_updated_at"]) - timedelta(days=4)).isoformat()
    if scenario == "new_hire":
        records.append({**records[0], "employee_id": "EMP-021", "full_name": "Morgan Diaz",
                        "email": "morgan.diaz@fictional.example", "department": "Engineering",
                        "manager_id": "EMP-001", "hire_date": settings.as_of.isoformat()})
    if scenario == "duplicate":
        records.extend([dict(records[0]), dict(records[0])])
    if scenario == "growth":
        for i in range(22, volume + 1):
            records.append({**records[0], "employee_id": f"EMP-{i:05}",
                            "full_name": f"Fictional Employee {i}",
                            "email": f"employee.{i}@fictional.example", "manager_id": "EMP-001"})
    return records


class SourceFailure(Exception):
    def __init__(self, code: str, attempts: int):
        self.code, self.attempts = code, attempts
        super().__init__(code)


class MockWorkday:
    def __init__(self, settings: Settings, scenario="normal", volume=5000):
        if scenario not in SCENARIOS:
            raise ValueError("Unknown scenario")
        self.settings, self.scenario = settings, scenario
        self.records = source_records(settings, scenario, volume)
        self.attempts = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.attempts += 1
        if self.scenario == "unavailable" or (self.scenario == "transient" and self.attempts <= 2):
            return httpx.Response(503, json={"error": "simulated_unavailable"})
        if self.scenario == "malformed":
            return httpx.Response(200, json={"workers": "not-a-list"})
        offset = int(request.url.params.get("offset", "0"))
        limit = 500
        next_offset = offset + limit
        return httpx.Response(200, json={
            "workers": self.records[offset:next_offset],
            "next_offset": next_offset if next_offset < len(self.records) else None,
        })

    def fetch(self) -> list[dict]:
        result, offset, visited = [], 0, set()
        with httpx.Client(transport=httpx.MockTransport(self.handle), timeout=5) as client:
            while offset is not None:
                if offset in visited:
                    raise SourceFailure("pagination_loop", self.attempts)
                visited.add(offset)
                for retry in range(3):
                    try:
                        response = client.get("https://workday.mock.local/workers", params={"offset": offset})
                        response.raise_for_status()
                        break
                    except (httpx.TransportError, httpx.HTTPStatusError):
                        if retry == 2:
                            raise SourceFailure("source_unavailable", self.attempts) from None
                        time.sleep(self.settings.retry_delay * (2 ** retry))
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("workers"), list) or "next_offset" not in payload:
                    raise SourceFailure("source_contract_invalid", self.attempts)
                if any(not isinstance(row, dict) for row in payload["workers"]):
                    raise SourceFailure("source_contract_invalid", self.attempts)
                result.extend(payload["workers"])
                offset = payload["next_offset"]
                if offset is not None and (type(offset) is not int or offset < 0):
                    raise SourceFailure("source_contract_invalid", self.attempts)
        return result
