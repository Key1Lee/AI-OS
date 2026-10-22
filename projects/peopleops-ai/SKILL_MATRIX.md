# PeopleOps engineering skill matrix

Updated: 2026-10-18. This is project-local evidence, not a hiring prediction or
another project's mastery record. Infrastructure written by the assistant is
not evidence of the learner's ability.

The learner reports experience with analytics engineering, Python, SQL, data
modeling, and automation, and difficulty translating some requirements into
independent application code. These are self-reports, not observed scores.

| Competency | Observable evidence required | Current readiness | Latest score / assistance | Next evidence opportunity |
| --- | --- | --- | --- | --- |
| Python | Independently implement and explain a pure transformation with validation | Unassessed | Not scored / no attempt | E01 normalize_employee |
| SQL | Correct grain, joins, aggregates, windows, and empty-group handling | Unassessed | Not scored / no attempt | E03 after E01/E02 |
| Data modeling | Explain keys, cardinality, history, and constraints using actual models | Unassessed | Not scored / no attempt | Employee/recruiting model discussion |
| APIs | Typed inputs/outputs, authentication, pagination, and meaningful errors | Unassessed | Not scored / no attempt | E08 and E11 |
| RAG | Retrieve permitted current evidence, measure recall, validate citations/refusals | Unassessed | Not scored / no attempt | E04–E06 |
| AI agents | Separate planning, permission, confirmation, commitment, and replay | Unassessed | Not scored / no attempt | E09/E10/E13 |
| Security | Enforce principal/record scope independently of model output | Unassessed | Not scored / no attempt | E07/E08 negative cases |
| Reliability | Diagnose a fault, bound retries, and demonstrate atomic recovery | Unassessed | Not scored / no attempt | E11/E12 and later isolated DEBUG scenario |
| System design | Justify boundaries using measured requirements and rejected alternatives | Unassessed | Not scored / no attempt | Design review after a completed milestone |

## Readiness states and mastery gate

Use **unassessed → attempted → demonstrated → mastered**. Record assistance
alongside every attempt; do not silently turn an assisted pass into independence.
An original exercise that passes is only demonstrated. Mastery requires:

1. An equivalent variation solved independently at Level 0.
2. Passing the required variation tests, with actual command/output evidence.
3. A satisfactory explanation of the rule, algorithm, edge cases, and production
   implications in the learner's own words.

Do not award mastery for recognizing, copying, or reading a solution. If evidence
is missing, write “not assessed,” not a numerical zero. Preserve improvement
history in INTERVIEW_LOG.md instead of replacing old scores.

## Patterns tied to business work

| Programming pattern | PeopleOps application | Status |
| --- | --- | --- |
| Filtering and validation | Workday record normalization | E01, current |
| Dictionaries / hash maps | Latest event per source ID | E02, pending |
| Grouping and aggregation | Department headcount and onboarding | E03, pending |
| Deduplication | Replayed recruiting deliveries | E02, pending |
| Sorting and ranking | Event versions and policy similarity | E02/E05, pending |
| Joins and lookups | Employee ownership and recruiting dimensions | E03/E08, pending |
| Window functions | Latest stage per candidate application | Later E03 variation, not assigned |
| State machines | Proposal → confirmation → committed receipt | E10, pending |
| Retry and backoff | Recover a failed mock API page | E11, pending |
| Pagination | Complete Workday/Greenhouse reads | E11, pending |
| Idempotency | Repeated write confirmation | E10, pending |
| Recursive processing | Employee management hierarchy | Later variation, not assigned |
| Graph traversal | Reporting-line cycles and reachability | Later variation, not assigned |
| Async API orchestration | Bounded concurrent reads across mock sources | Later extension, not assigned |

Only E01 is assigned now. These mappings are a curriculum map, not proof that
the features or competencies are complete.
