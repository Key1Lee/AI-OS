# Business requirements

An HR employee asks, “What was everyone's company survey score at Samsara over
the last three years?” This local interview demonstration answers with aggregate,
entirely fictional engagement data for 2024, 2025 and 2026 YTD through October 21.
The October 22 population update requires 5,000 fictional eligible employees annually
across Human Resources, Marketing, Engineering & Product, Sales, and Customer
Success & Support. Annual totals, department totals, parser filters, charts, CSV
exports and independent reference comparisons must use that same expanded source.

It must be understandable to a Senior Analytics Engineer evaluating an AI and
People Analytics workflow.

Success requires a real browser → Next.js → n8n webhook → mock Qualtrics → metrics
→ knowledge retrieval → grounded response pipeline. The existing local Qwen model
must interpret natural questions and select grounded facts and passages, including
possessive department names, rankings and general survey methodology. Explicit
filters override inferred scope; unsupported data must be declined. Every dashboard and chat
metric must match an independently implemented Python reference for the same
source checksum. Filtering must preserve respondent weighting and response-rate
denominators. Tampering must fail validation and withhold numerical findings.
The five example questions, unavailable n8n, missing records, unknown departments,
duplicates and corrupt references must be exercised. The application must build,
type check, lint and start through Docker Compose without paid APIs or keys.

Excluded: real survey integration, employee lookup, individual answers, LLM-based
arithmetic, authentication services, enterprise infrastructure, cloud deployment,
statistical significance tests, causal claims and production readiness.

Privacy assumptions: the fixtures contain only fictional submission IDs,
departments, timestamps and integer answers. No identities or confidential data
exist. Raw mock exports are available locally for inspection; chat and dashboard
expose aggregates only. Local ports bind to loopback. “Samsara” describes the
requested fictional interview scenario and does not imply endorsement or actual
company results.
