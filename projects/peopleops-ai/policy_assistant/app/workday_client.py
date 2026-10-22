from datetime import timedelta
import json
import time
from typing import Protocol
from urllib.parse import unquote

import httpx
from pydantic import ValidationError

from app.models import PTORecord
from app.permissions import may_read_pto
from app.mock_store import transaction
from app.rules import default_rules


class RecordError(Exception):
    """A safe source status; never carries source payloads or employee identifiers."""
    def __init__(self, status, attempts=0):
        self.status, self.attempts = status, attempts
        super().__init__(status)


class PTOClient(Protocol):
    def get_pto(self, principal, target_employee): ...


class MockWorkdayTransport(httpx.BaseTransport):
    """Simulate a read-only Workday HTTP source with repeatable failure scenarios."""
    def __init__(self, fixture_path=None, scenario="normal", database_path=None):
        self.database_path = database_path
        self.records = json.loads(fixture_path.read_text()) if fixture_path and database_path is None else []
        self.scenario, self.calls = scenario, 0

    def handle_request(self, request):
        self.calls += 1
        scenario = self.scenario
        if scenario == "timeout":
            raise httpx.ReadTimeout("mock timeout", request=request)
        if scenario in ("unavailable", "rate_limited") or (scenario == "intermittent" and self.calls <= 2):
            return httpx.Response(429 if scenario == "rate_limited" else 503, headers={"Retry-After": "0.01"})
        if scenario == "malformed":
            return httpx.Response(200, json={"pto_balance": "unknown"})
        target = unquote(request.url.path.rsplit("/", 1)[-1])
        tenant = request.headers.get("X-Mock-Tenant")
        if scenario == "slow":
            time.sleep(.025)
        if self.database_path is not None:
            with transaction(self.database_path) as conn:
                row = conn.execute("SELECT record FROM mock_workday WHERE tenant=? AND employee_id=?", (tenant, target)).fetchone()
                try:
                    record = json.loads(row[0]) if row else None
                except (ValueError, TypeError):
                    return httpx.Response(200, json={})
                if row and not isinstance(record, dict):
                    return httpx.Response(200, json={})
        else:
            record = next((r for r in self.records if r["employee_id"] == target and r["tenant"] == tenant), None)
        if scenario == "missing" or record is None:
            return httpx.Response(404)
        record = dict(record)
        if scenario == "stale":
            record["as_of_date"] = "2020-01-01"
        if scenario == "wrong_owner":
            record["employee_id"] = "EMP999"
        return httpx.Response(200, json=record)


def validate_record(record, principal, target_employee, settings, rulebook=None):
    """Recheck a typed adapter result against ownership and the configured freshness limit."""
    rules = rulebook or default_rules()
    try:
        record = PTORecord.model_validate(record.model_dump() if isinstance(record, PTORecord) else record)
    except ValidationError as error:
        raise RecordError("malformed") from error
    if record.employee_id != target_employee or not may_read_pto(principal, record.employee_id, record.tenant, rules.security):
        raise RecordError("invalid_scope")
    age = settings.as_of_date-record.as_of_date
    if age < timedelta(0) or age > timedelta(days=min(settings.max_record_age_days, rules.business.max_record_age_days)):
        raise RecordError("stale")
    return record


class MockWorkdayClient:
    def __init__(self, settings, transport=None, sleep=time.sleep, rulebook=None):
        self.settings = settings
        self.transport = transport or MockWorkdayTransport(database_path=settings.database_path)
        self.rulebook = rulebook or default_rules()
        self.sleep = sleep

    def get_pto(self, principal, target_employee):
        """Authorize a record read, retry transient failures within bounds, and validate owner/value/freshness."""
        if not may_read_pto(principal, target_employee, security=self.rulebook.security):
            raise RecordError("denied")
        last_failure = "unavailable"
        for attempt in range(1, self.settings.workday_attempts + 1):
            retry_after = self.settings.workday_backoff_seconds * 2 ** (attempt - 1)
            try:
                with httpx.Client(transport=self.transport, timeout=self.settings.workday_timeout_seconds) as client:
                    response = client.get("https://mock-workday.invalid/pto/" + target_employee,
                                          headers={"X-Mock-Tenant": principal.tenant})
                if response.status_code == 404:
                    raise RecordError("missing", attempt)
                if response.status_code not in (429, 503):
                    response.raise_for_status()
                    try:
                        record = PTORecord.model_validate_json(response.content)
                    except ValidationError as exc:
                        raise RecordError("malformed", attempt) from exc
                    try:
                        record = validate_record(record, principal, target_employee, self.settings, self.rulebook)
                    except RecordError as error:
                        raise RecordError(error.status, attempt) from error
                    return record, attempt
                last_failure = "rate_limited" if response.status_code == 429 else "upstream_503"
                try:
                    retry_after = max(retry_after, min(float(response.headers.get("Retry-After", 0)), 0.2))
                except ValueError:
                    pass
            except httpx.TimeoutException:
                last_failure = "timeout"
            except httpx.TransportError:
                last_failure = "unavailable"
            except httpx.HTTPStatusError as exc:
                raise RecordError("unavailable", attempt) from exc
            if attempt < self.settings.workday_attempts:
                self.sleep(retry_after)
        raise RecordError(last_failure, self.settings.workday_attempts)
