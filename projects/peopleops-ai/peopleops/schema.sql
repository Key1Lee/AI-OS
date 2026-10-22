PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL CHECK(length(trim(full_name)) > 0),
    email TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','leave','terminated','prehire')),
    hire_date TEXT NOT NULL,
    termination_date TEXT,
    manager_id TEXT REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
    salary_cents INTEGER NOT NULL CHECK(salary_cents >= 0),
    source_updated_at TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    CHECK(termination_date IS NULL OR termination_date >= hire_date),
    CHECK((status = 'terminated' AND termination_date IS NOT NULL) OR
          (status != 'terminated' AND termination_date IS NULL))
);
CREATE TABLE IF NOT EXISTS principals (
    principal_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('employee','hr','analyst')),
    employee_id TEXT REFERENCES employees(employee_id),
    token_hash TEXT NOT NULL UNIQUE,
    CHECK(role != 'employee' OR employee_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY, scenario TEXT NOT NULL,
    started_at TEXT NOT NULL, finished_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running','success','failed')),
    received INTEGER NOT NULL DEFAULT 0, accepted INTEGER NOT NULL DEFAULT 0,
    rejected INTEGER NOT NULL DEFAULT 0, duplicates INTEGER NOT NULL DEFAULT 0,
    changed INTEGER NOT NULL DEFAULT 0, unchanged INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0, duration_ms REAL,
    source_latest_at TEXT, error_code TEXT
);
CREATE TABLE IF NOT EXISTS raw_employees (
    run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    row_number INTEGER NOT NULL, payload TEXT NOT NULL,
    PRIMARY KEY(run_id,row_number)
);
CREATE TABLE IF NOT EXISTS quarantine (
    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    row_number INTEGER NOT NULL, employee_id TEXT, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hr_requests (
    request_id TEXT PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    subject TEXT NOT NULL, description TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('payroll','benefits','leave','onboarding','employee_relations','general')),
    team TEXT NOT NULL, routing_confidence REAL NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('open','in_progress','resolved')),
    priority TEXT NOT NULL CHECK(priority IN ('normal','high')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolved_at TEXT,
    idempotency_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
    UNIQUE(employee_id,idempotency_key)
);
CREATE INDEX IF NOT EXISTS requests_status_created ON hr_requests(status,created_at);
CREATE TABLE IF NOT EXISTS onboarding_tasks (
    task_id TEXT PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    kind TEXT NOT NULL, owner_team TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','completed')),
    due_date TEXT NOT NULL, completed_at TEXT,
    UNIQUE(employee_id,kind)
);
CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK(visibility IN ('public','hr')),
    body TEXT NOT NULL, version INTEGER NOT NULL,
    effective_date TEXT NOT NULL, available INTEGER NOT NULL CHECK(available IN (0,1))
);
CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL, payload TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','sent','failed')),
    attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
    delivered_at TEXT, error_code TEXT
);
CREATE TABLE IF NOT EXISTS slack_messages (
    message_id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE,
    channel TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
    actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN ('allowed','denied','failed')),
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS http_observations (
    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
    route TEXT NOT NULL, method TEXT NOT NULL, status_code INTEGER NOT NULL,
    duration_ms REAL NOT NULL
);
