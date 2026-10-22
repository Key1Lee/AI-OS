"""Deterministic synthetic truth; seed=42, anchor=2026-10-01. No source cleaning here."""
from datetime import date, timedelta
from pathlib import Path
import json
import random

ANCHOR = date(2026, 10, 1)
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "enterprise.json"

POLICIES = [
    ("PTO", "Paid time off", "all", "Annual allowance", "Full-time employees receive 160 hours of PTO per calendar year.", "Request process", "Submit PTO at least 5 business days before leave. Manager approval is required."),
    ("BEN", "Benefits enrollment", "all", "Eligibility", "Active full-time employees are eligible for medical benefits from their hire date.", "Enrollment", "Enroll within 30 calendar days of your hire date."),
    ("ONB", "New hire onboarding", "all", "First day", "Complete identity verification and security training on your first day.", "Equipment", "Your manager requests a laptop before your start date."),
    ("EXP", "Expense reimbursement", "all", "Receipts", "Itemized receipts are required for expenses above 25 USD.", "Submission", "Submit expenses within 30 calendar days of purchase."),
    ("PAR", "Parental leave", "all", "Allowance", "Eligible employees receive 16 weeks of paid parental leave.", "Notice", "Give HR 30 calendar days of notice when practical."),
    ("PAY", "Payroll", "all", "Schedule", "Payroll is paid on the 15th and final business day of each month.", "Missing pay", "For missing or incorrect pay, prepare a Payroll support ticket with the pay period. Do not include bank account numbers."),
    ("REM", "Remote work", "all", "Location", "Employees must work from their approved country of employment.", "Changes", "Discuss a permanent work location change with HR before moving."),
    ("SICK", "Sick leave", "all", "Allowance", "Employees receive 80 hours of sick leave per year.", "Notice", "Notify your manager before your scheduled start when possible."),
    ("SEC", "Security training", "all", "Completion", "All employees complete security training annually.", "Reporting", "Report suspected phishing using the security reporting channel."),
    ("TRV", "Business travel", "all", "Approval", "Manager approval is required before booking business travel.", "Class", "Book economy class for flights shorter than 6 hours."),
    ("HOL", "Company holidays", "all", "Calendar", "The local holiday calendar follows the employee's country of employment.", "Questions", "Ask HR if your local holiday is missing from the calendar."),
    ("EDU", "Learning allowance", "all", "Allowance", "Employees may request up to 1000 USD annually for approved learning.", "Approval", "Get manager approval before purchasing a course."),
    ("REC", "Recruiter operations", "recruiter", "Candidate notes", "Candidate notes are accessible only to assigned recruiters and HR administrators.", "Retention", "Remove candidate records after the documented retention period."),
    ("COMP", "Compensation planning", "hr_admin", "Restricted planning", "Compensation planning worksheets are restricted to HR administrators.", "Sharing", "Do not share individual compensation data through employee chat."),
    ("MGR", "Manager guide", "manager", "Check-ins", "Managers hold a check-in with direct reports every two weeks.", "Escalation", "Escalate employee relations concerns to HR."),
]


def generate(seed: int = 42) -> dict:
    rng = random.Random(seed)
    employees = []
    departments = ["Engineering", "Sales", "Operations", "People"]
    for i in range(1, 121):
        status = "terminated" if i % 12 == 0 else "leave" if i % 17 == 0 else "active"
        hire = ANCHOR - timedelta(days=rng.randint(20, 1200))
        employees.append({
            "employee_id": f"EMP-{i:03}", "full_name": "Maya Chen" if i == 1 else f"Synthetic Person {i:03}",
            "email": f"person{i:03}@example.test", "department": departments[(i - 1) % 4],
            "manager_id": None if i <= 4 else f"EMP-{(i - 1) % 4 + 1:03}",
            "status": status, "hire_date": hire.isoformat(),
            "termination_date": (ANCHOR - timedelta(days=i % 28)).isoformat() if status == "terminated" else None,
            "pto_hours": 80 if i == 1 else rng.randrange(0, 161, 8), "benefits_eligible": status != "terminated",
            "source_updated_at": "2026-10-01T08:00:00+00:00",
        })
    jobs = [{"job_id": f"JOB-{i:03}", "title": f"{departments[(i - 1) % 4]} specialist {i:02}",
             "department": departments[(i - 1) % 4], "status": "open", "opened_on": "2026-08-01"} for i in range(1, 25)]
    candidates = [{"candidate_id": f"CAN-{i:03}", "full_name": f"Synthetic Candidate {i:03}",
                   "email": f"candidate{i:03}@example.test", "job_id": f"JOB-{(i - 1) % 24 + 1:03}"} for i in range(1, 81)]
    events = []
    for i, candidate in enumerate(candidates):
        for j, stage in enumerate(["applied", "screen", "interview"]):
            events.append({"event_id": f"EVT-{i * 3 + j + 1:04}", "candidate_id": candidate["candidate_id"], "stage": stage,
                           "occurred_at": f"2026-09-{j + 10:02}T09:00:00+00:00", "source_updated_at": "2026-10-01T08:00:00+00:00"})
    policies = []
    for code, title, audience, h1, b1, h2, b2 in POLICIES:
        policies.append({"policy_id": code, "version": 2, "title": title, "audience": audience,
                         "effective_on": "2026-01-01", "retired": False,
                         "sections": [{"section_id": "1", "heading": h1, "body": b1}, {"section_id": "2", "heading": h2, "body": b2}]})
    policies.append({"policy_id": "PTO", "version": 1, "title": "Paid time off (superseded)", "audience": "all",
                     "effective_on": "2025-01-01", "retired": True,
                     "sections": [{"section_id": "1", "heading": "Old allowance", "body": "Full-time employees receive 120 hours of PTO per calendar year."}]})
    tickets = [{"ticket_id": f"TKT-{i:03}", "employee_id": f"EMP-{i:03}", "category": "Payroll" if i % 3 == 1 else "Benefits",
                "subject": "Missing payroll payment" if i % 3 == 1 else "Enrollment question",
                "status": "resolved" if i % 4 == 0 else "open", "created_at": "2026-09-30T09:00:00+00:00"} for i in range(1, 61)]
    tasks = [{"task_id": f"ONB-{i:03}", "employee_id": f"EMP-{(i - 1) // 3 + 1:03}",
              "kind": ["security", "equipment", "orientation"][(i - 1) % 3], "status": "done" if i % 2 == 0 else "pending",
              "due_on": "2026-10-05"} for i in range(1, 61)]
    raw = [dict(e) for e in employees]
    raw[0]["full_name"] = "  Maya   Chen  "
    raw[0]["email"] = " PERSON001@EXAMPLE.TEST "
    raw[0]["status"] = " Active "
    dirty = [dict(raw[0], employee_id="EMP-999", email=None), dict(raw[1], hire_date="not-a-date"), dict(raw[2], pto_hours=-8)]
    duplicate = dict(events[0], source_updated_at="2026-09-30T08:00:00+00:00", stage="screen")
    return {"metadata": {"seed": seed, "as_of": ANCHOR.isoformat(), "synthetic": True, "version": "training-v1"},
            "employees": employees, "raw_employees": raw, "invalid_employees": dirty, "jobs": jobs, "candidates": candidates,
            "recruiting_events": events, "raw_recruiting_events": events + [duplicate, dict(events[2])],
            "policies": policies, "tickets": tickets, "onboarding_tasks": tasks,
            "slack_messages": [{"message_id": "MSG-001", "employee_id": "EMP-001", "text": "Employee needs help with payroll", "channel": "hr-help"}]}


def load() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


if __name__ == "__main__":
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(generate(), indent=2) + "\n")
    print(f"Wrote reproducible synthetic fixtures to {FIXTURE_PATH}")
