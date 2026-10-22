"""Regenerate packaged fictional examples. Never reads enterprise systems."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parents[1] / "peopleops" / "fixtures"
OUT.mkdir(exist_ok=True)
names = ["Maya Chen", "Jordan Lee", "Avery Patel", "Sam Rivera", "Riley Morgan",
         "Casey Brooks", "Taylor Kim", "Alex Okafor", "Jamie Park", "Drew Santos",
         "Robin Shah", "Quinn Ellis", "Blair Nguyen", "Skyler James", "Emery Ross",
         "Finley Reed", "Harper Wu", "Sage Martin", "Rowan Bell", "Reese Flores"]
records = []
for i, name in enumerate(names, 1):
    records.append({
        "employee_id": f"EMP-{i:03}", "full_name": name,
        "email": name.lower().replace(" ", ".") + "@fictional.example",
        "department": ["People", "Engineering", "Operations", "Sales"][((i-1)//4) % 4],
        "status": "active", "hire_date": "2024-04-01" if i < 11 else "2026-10-05",
        "termination_date": None, "manager_id": None if i == 1 else "EMP-001",
        "salary_cents": 7000000 + i * 150000, "source_updated_at": "2026-10-17T00:00:00+00:00",
    })
records[1]["email"] = "  JORDAN.LEE@fictional.example  "
records[2]["status"] = " ACTIVE "
records[3]["hire_date"] = "04/01/2024"
records[13]["status"] = "leave"
records[14].update(status="terminated", termination_date="2026-10-07")
records[15]["full_name"] = ""
records[16]["email"] = None
records[17]["hire_date"] = "2026-02-30"
records[18]["status"] = "mystery"
records[19].update(status="prehire", hire_date="2026-10-24")
# Two additional source rows represent duplicate deliveries, not extra employees.
records.append({**records[2], "status": "active", "source_updated_at": "2026-10-17T00:01:00+00:00"})
records.append({**records[3], "source_updated_at": "2026-10-16T00:00:00+00:00"})
(OUT / "employees.json").write_text(json.dumps(records, indent=2) + "\n")

policies = [
    ("POL-001", "Payroll & payslips", "payroll", "public",
     "In this fictional company, payroll is paid on the 15th and final business day of each month. Payslips appear in the employee portal after payroll finishes.\n\nFor missing pay, an incorrect payslip, or a direct deposit issue, submit a payroll request to the Payroll team. Never put bank account numbers in an HR ticket."),
    ("POL-002", "Vacation & time off", "leave", "public",
     "Full-time employees in this fictional company receive 20 days of vacation each calendar year. Request vacation in the employee portal and wait for manager approval before booking travel.\n\nFor urgent leave or a balance discrepancy, contact People Operations through an HR request. Individual eligibility must be confirmed by HR."),
    ("POL-003", "Health benefits enrollment", "benefits", "public",
     "New hires have 30 days from their start date to enroll in the fictional company's health benefits through the employee portal.\n\nContact the Benefits team for enrollment errors or questions about eligibility. This sample policy does not provide medical or insurance advice."),
    ("POL-004", "Your first week", "onboarding", "public",
     "New hires receive three onboarding tasks: verify profile details, complete orientation, and confirm equipment delivery. Complete these tasks by the end of your first week.\n\nThe IT team handles equipment and People Operations handles orientation. Onboarding reminders contain request identifiers, never confidential employee details."),
    ("POL-005", "Remote work & equipment", "general", "public",
     "Employees may request remote work through their manager. The fictional company's standard arrangement allows two remote days each week after manager approval.\n\nReport equipment problems to IT and keep company devices secured when working remotely."),
    ("POL-006", "Updating your employee profile", "general", "public",
     "Update your mailing address and emergency contact through the employee portal. People Operations reviews changes to legal name or employment details.\n\nNever send identity documents or bank information through a public Slack channel. Use the approved secure HR process."),
    ("POL-007", "Compensation review procedure", "employee_relations", "hr",
     "HR-only fictional procedure: compensation reviews require approval from the People Partner and Finance. The sample internal review budget is 4 percent.\n\nDo not share internal review budgets or individual compensation decisions with other employees."),
    ("POL-008", "Employee relations case handling", "employee_relations", "hr",
     "HR-only fictional procedure: sensitive employee relations cases go directly to the People Partner team. Limit access to assigned HR staff and keep investigation material outside routine notifications."),
]
(OUT / "policies.json").write_text(json.dumps([
    dict(policy_id=p[0], title=p[1], category=p[2], visibility=p[3], body=p[4],
         version=1, effective_date="2026-10-01", available=1) for p in policies
], indent=2) + "\n")
