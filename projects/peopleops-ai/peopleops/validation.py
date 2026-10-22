"""Pure functions: raw dictionaries in; clean dictionaries or reasons out."""
from datetime import date, datetime, timezone
import re

STATUSES = {"active", "leave", "terminated", "prehire"}


def parse_date(value) -> str:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError("invalid_date")


def clean_employee(raw: dict, as_of: date) -> dict:
    employee_id = str(raw.get("employee_id") or "").strip()
    name = str(raw.get("full_name") or "").strip()
    email = str(raw.get("email") or "").strip().lower()
    department = str(raw.get("department") or "").strip()
    status = str(raw.get("status") or "").strip().lower()
    if not re.fullmatch(r"EMP-\d{3,6}", employee_id):
        raise ValueError("invalid_employee_id")
    if not name or not department:
        raise ValueError("missing_required_field")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("invalid_email")
    if status not in STATUSES:
        raise ValueError("invalid_status")
    hire = parse_date(raw.get("hire_date"))
    termination = parse_date(raw["termination_date"]) if raw.get("termination_date") else None
    if termination and (termination < hire or termination > as_of.isoformat()):
        raise ValueError("invalid_termination_date")
    if (status == "terminated") != bool(termination):
        raise ValueError("termination_status_mismatch")
    if status in {"active", "leave"} and hire > as_of.isoformat():
        raise ValueError("future_active_hire")
    salary = raw.get("salary_cents")
    if type(salary) is not int or salary < 0:
        raise ValueError("invalid_salary")
    try:
        timestamp = datetime.fromisoformat(str(raw.get("source_updated_at")))
        if timestamp.tzinfo is None:
            raise ValueError()
        timestamp = timestamp.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        raise ValueError("invalid_source_timestamp") from None
    manager = str(raw.get("manager_id") or "").strip() or None
    if manager == employee_id:
        raise ValueError("self_manager")
    return dict(employee_id=employee_id, full_name=name, email=email, department=department,
                status=status, hire_date=hire, termination_date=termination, manager_id=manager,
                salary_cents=salary, source_updated_at=timestamp)
