# Enterprise functions, in elementary language

This tour covers `app.main`, the SQLite enterprise reference. The earlier
pgvector app's tour remains in `functions.md`.

| Function or contract | What it does and why it exists |
| --- | --- |
| `RuleBook` / `match()` | Load typed business, routing and security YAML and describe the rule that actually ran. The client cannot edit those rules or grant permissions. |
| `ExecutionTrace.step()` / `complete()` | Time actual component work and record its outcome. Unexecuted stages are marked skipped instead of receiving invented timings. |
| `seed_enterprise_data()` | Load synthetic identities and Workday records into SQLite atomically. Unchanged fixture digests preserve database edits. |
| `SQLiteIdentityProvider.entries` | Read the runtime identity records from SQLite. Revoking an identity or scoped grant changes subsequent request authorization. |
| `validate_record()` | Revalidate a source adapter's typed result for value, owner, tenant and freshness. This also protects the response when a different adapter is injected. |
| `TestJobRunner.start()` / `_run()` | Start one allowlisted real subprocess with isolated reports and a deadline. No HTTP input can choose an arbitrary command, environment or output path. |
| `read_results()` | Read actual JUnit, coverage and evaluation artifacts into safe counts and metrics. It excludes assertion payloads and parameter text from the web response. |
| `run_worker()` | Execute pytest for the selected directory or the complete suite. Full evaluations run only after the entire selected regression suite succeeds. |
| `TestJobRunner.get()` / `recent()` | Return operator-authorized job reports with a current-source label. Reports from another tenant are unavailable. |
| `stop_process()` | Terminate only the owned worker group when the deadline or app shutdown requires it. The tested group cleanup targets macOS/Linux. |
| `HRSettings.configured()` | Reads the proposed demo settings and applies real environment overrides. This keeps dates, limits and file locations out of business logic. |
| `create_app()` | Connects the handlers, identities, sources and safety checks. Tests can supply different source adapters without changing the business rules. |
| `RateLimiter.check()` | Counts recent requests for one authenticated identity. It rejects excess requests before any HR source is read. |
| `authenticate_session()` | Checks a bearer session against server-owned identity records. Request fields cannot choose the employee, role or permissions. |
| `slack_signature()` / `verify_slack()` | Sign or verify the exact request bytes and timestamp. A valid Slack signature proves transport origin, so a separate employee session is still required. |
| `MockIdentityProvider.credential_entries()` | Converts the synthetic identity fixture into validated principals. This is the replacement point for an approved enterprise identity adapter. |
| `MockIdentityProvider.bind_slack()` | Checks that the signed workspace and Slack user match the employee session. A caller cannot substitute another Slack user to gain their access. |
| `may_read_pto()` | Allows a self-service PTO read or an explicitly scoped delegation with an approved mock purpose. An HR role by itself does not grant access to personal records. |
| `may_read_document()` | Checks tenant, lifecycle, dates, country, employee group, role and classification. Rejected documents never enter search ranking or answer construction. |
| `route_intent()` | Chooses one of seven workflows and identifies an explicit record target. It cannot grant permissions or supply employee facts. |
| `Orchestrator.handle()` | Runs the selected workflow in the required order and records its component trace. It keeps policy evidence separate from personal source records. |
| `PTOClient` | Defines the small read-only contract for a future employee-record adapter. It exposes no payroll, salary or record-writing method. |
| `MockWorkdayTransport.handle_request()` | Returns synthetic HTTP responses or a named failure. It exercises real client error handling without contacting Workday. |
| `MockWorkdayClient.get_pto()` | Checks access before reading, retries only bounded transient failures, and validates the returned owner, number, unit and date. Invalid or stale source data cannot become an answer. |
| `authorized_chunks()` | Selects the current governed version, applies permissions, and verifies source and chunk integrity. An old index entry cannot restore removed inventory access. |
| `search_terms()` / `search()` | Rank authorized text using deterministic local word matching. This makes the mock reproducible while preserving an adapter boundary for a future retriever. |
| `record_response()` | Prints the exact source balance, unit and date. A model never estimates or rewrites the number. |
| `policy_response()` | Quotes a sufficiently relevant approved passage with a verifiable citation. It abstains when evidence is missing or structured policy facts conflict. |
| `simple_response()` | Builds a consistent denial, clarification, abstention or handoff. These responses contain no invented HR facts. |
| `configure_logging()` / `write_audit()` | Emit and store only allowlisted operational fields. Questions, source content, employee IDs, balances and credentials are excluded. |
| `percentile()` / `metrics()` | Summarize observed request timings and index ingestion status. These local measurements do not establish a production SLA. |
| `transaction()` / `initialize()` | Open a short SQLite transaction and prepare the local schema. Failed changes roll back together. |
| HTTP `execute()` | Binds duplicate receipts to the authenticated principal and request body. Concurrent copies reuse one result rather than repeating a protected read. |
| `extract_documents()` | Reads bounded JSONL source files and preserves safe line references. Malformed or oversized input receives an explicit rejection reason. |
| `load_registry()` / `validate_document()` | Load the independent approval inventory and compare source metadata and content digests. A source cannot approve itself by changing its own metadata. |
| `rejection_reason()` | Rejects disallowed classifications, lifecycle states, dates and recognizable injected instructions. Runtime permissions still apply after ingestion. |
| `chunk_document()` | Splits approved text at headings and word boundaries while retaining exact source words. Stable chunk IDs make citations reproducible. |
| `sync_registry()` | Mirrors active inventory membership while retaining immutable history. Removing a document from the inventory denies its old indexed content. |
| `index_document()` | Writes a new version once or recognizes an identical replay. Changed chunk settings replace derived chunks without duplicating document versions. |
| `run_pipeline()` | Executes ingestion atomically and records counts and rejection reasons. The HTTP admin route and command line use the same pipeline. |
| `evaluate_routing()` | Compares workflow choices with independently written labels. It catches routing regressions separately from API tests. |
| `evaluate_retrieval()` | Compares retrieved document IDs with gold labels and independent access allowlists. It reports recall, returned-result precision, ranking and observed exposure. |
| `citation_valid()` / `evaluate_grounding()` | Check exact source quotes, fixture facts, PTO values and safe response statuses. They measure source support and labeled facts, not comprehensive semantic understanding. |
| `evaluate_security()` | Exercises adversarial requests and checks that denied cases expose no protected facts or tool reads. Its result is bounded to the tested attacks. |
| `LocalQwenJudge.judge()` | Optionally asks an existing local model for a structured semantic assessment. It has no tools, cannot authorize access and cannot overrule release gates. |
| `reliability()` | Times real in-process HTTP handling and sends concurrent requests. It records local p50, p95 and p99 separately from proposed production targets. |
| `traceability_report()` | Compares requirements, actual test markers, source paths and evaluation references. It reports untested requirements and unmapped tests instead of hiding gaps. |
| `fingerprint()` / `test_evidence()` | Bind passing pytest evidence to the selected Python, configuration, fixture and label files. Old test results cannot certify a changed runtime. |
| `evaluate_all()` | Runs the independent evaluation layers and writes the release decision. A failed required gate returns a failing process exit code for CI. |

Unit tests check small rules such as identity, ownership and numeric formatting.
Integration tests check that those rules remain correct across component boundaries.
Security tests try identity substitution, metadata tampering, injection and data
leakage. Signed Slack end-to-end tests exercise the complete request path, including
duplicate and concurrent events. The labeled evaluation datasets measure behavior
across examples separately from those implementation tests.
