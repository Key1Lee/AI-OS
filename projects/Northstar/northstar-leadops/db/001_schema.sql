BEGIN;

CREATE TABLE IF NOT EXISTS lead_events (
  idempotency_key TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  event_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
  attempt_count INTEGER NOT NULL DEFAULT 1 CHECK (attempt_count > 0),
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locked_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  crm_contact_id TEXT,
  fit_score INTEGER CHECK (fit_score BETWEEN 0 AND 100),
  fit_tier TEXT CHECK (fit_tier IN ('HOT', 'WARM', 'COLD', 'MANUAL_REVIEW')),
  ai_confidence NUMERIC(4,3) CHECK (ai_confidence BETWEEN 0 AND 1),
  crm_write_status TEXT,
  notification_status TEXT,
  last_error_code TEXT
);

CREATE INDEX IF NOT EXISTS lead_events_status_locked_idx
  ON lead_events (status, locked_at);

ALTER TABLE lead_events ADD COLUMN IF NOT EXISTS crm_write_status TEXT;
ALTER TABLE lead_events ADD COLUMN IF NOT EXISTS notification_status TEXT;
ALTER TABLE lead_events DROP CONSTRAINT IF EXISTS lead_events_source_event_id_key;

CREATE TABLE IF NOT EXISTS workflow_effects (
  effect_key TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL REFERENCES lead_events(idempotency_key),
  effect_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'unknown', 'failed')),
  attempt_count INTEGER NOT NULL DEFAULT 1 CHECK (attempt_count > 0),
  locked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  remote_id TEXT,
  last_error_code TEXT
);

CREATE INDEX IF NOT EXISTS workflow_effects_event_idx
  ON workflow_effects (idempotency_key, effect_type);

CREATE TABLE IF NOT EXISTS workflow_errors (
  id BIGSERIAL PRIMARY KEY,
  idempotency_key TEXT,
  workflow_name TEXT NOT NULL,
  execution_id TEXT,
  node_name TEXT,
  error_code TEXT NOT NULL,
  error_message TEXT NOT NULL,
  retryable BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS workflow_errors_created_at_idx
  ON workflow_errors (created_at DESC);

COMMIT;
