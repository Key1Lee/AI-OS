# Business context and data contracts

The fictional company supports employees with policy questions, personal PTO
information, recruiting operations, and HR requests. A payroll question is the
first motivating workflow: read the policy, prepare the correct support request,
show a preview, then write only after the employee confirms.

All names, messages, policies, and email addresses are synthetic. Policy amounts
are invented training rules, not employment, tax, or legal advice.

## Fixture inventory

Seed 42; fixed business date **2026-10-01**. Regeneration is byte-stable.

| Dataset | Count | Grain / key |
| --- | ---: | --- |
| Employees | 120 | One current employment record / employee_id |
| Raw employees | 120 + 3 separate invalid examples | One source delivery; raw values may be dirty |
| Jobs | 24 | One job opening / job_id |
| Candidates | 80 | One candidate application to one job / candidate_id |
| Recruiting events | 240 canonical; 242 delivered | One stage event / event_id; duplicates exist in raw delivery |
| Policy documents | 16 versions across 15 policy IDs | policy_id + version |
| Policy sections / seeded chunks | 31 / 31 | policy_id + version + section_id; chunk adds ordinal |
| HR requests | 60 | One support ticket / ticket_id |
| Onboarding | 60 | One task per employee + kind |
| Slack source | 1 | One synthetic message / message_id |
| Evaluation scenarios | 36 | One defined request expectation / scenario ID |

`EMP-001` is Maya Chen, Engineering, hired 2026-01-26, active, with 80 PTO
hours. `TKT-001` belongs to her and is an open Payroll ticket. `EVT-0001`
appears again with an older version; the older copy must not replace the newest.
PTO v1 says 120 hours and is retired; v2 says 160 hours and is current.

## Relationships and modeling limits

Employees have zero or one manager; managers have many reports. Tickets and
onboarding tasks point to employees. Candidate applications point to jobs;
events point to candidate applications. Policies have versioned sections;
chunks reference exact sections. Proposals bind actor, tool, arguments, hash,
and expiration; receipts enforce unique actor/key and proposal execution.

Foreign keys and unique constraints enforce basic relational integrity.
Authorization is application logic in E07/E08; database constraints alone do not
authorize readers. This lab has no row-level PostgreSQL security.

The current employee table is not a history table and cannot represent rehires
or multiple simultaneous employments. A candidate applies to one job in these
fixtures; production modeling would separate people and applications. These
limitations must be mentioned when interpreting metrics.

## Metric definitions for E03

Use `:as_of=2026-10-01` and `:period_start=2026-09-01` as bound DATE parameters.

| Metric | Definition and expected shape | Common trap |
| --- | --- | --- |
| Current headcount | Employee hire_date <= as_of and termination_date is null or > as_of, excluding prehire. Group by department; output department, headcount sorted by department. Fixture total 110. | Joining tickets first multiplies employees with many requests |
| Turnover | Departures in [period_start, as_of]; opening and closing headcount at those dates; departures / ((opening+closing)/2). Return one row. NULL rate when denominator=0. | Using today's status to reconstruct past headcount loses later departures |
| Hiring funnel | Count distinct candidate_id reaching each stage; output stage, candidates. Applied/screen/interview each 80. | Counting raw deliveries or joining every candidate event to every ticket |
| Onboarding | Assigned/completed task counts per employee department; completion_rate=completed/assigned, NULL when none; retain departments with zero tasks. | INNER JOIN drops departments; integer division truncates rates |

Departure day is excluded from point-in-time headcount. Onboarding includes
all seeded assigned tasks. Funnel counts stages reached, not a candidate's
latest stage. A conversion ratio needs an explicit cohort/window before it can
be interpreted; this exercise does not silently invent one.

## Ingestion contract

Required fields are the `EmployeeRecord` fields. Normalize whitespace in names,
trim and lowercase emails/status, parse ISO dates, require aware source timestamps,
nonnegative integer PTO, supported statuses, and a valid email containing one
`@` and a nonempty local/domain part. Null manager/departure is allowed.
Reject impossible temporal combinations and unexpected missing required fields.

E02 chooses latest source timestamps per event ID; equal timestamps use the
last input delivery. E12 accepts newer employee versions, preserves older ones,
and never treats absent IDs as deletions. The raw synthetic JSON stays available
for debugging; it is not ingested automatically through solved exercise code.
