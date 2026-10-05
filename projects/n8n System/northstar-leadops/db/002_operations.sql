-- Inspect work that needs an operator decision.
SELECT idempotency_key, status, attempt_count, locked_at, last_error_code,
       crm_write_status, notification_status
FROM lead_events
WHERE status <> 'completed'
   OR notification_status IN ('unknown', 'suppressed_existing_effect')
ORDER BY received_at;

-- Approve one controlled replay after the underlying fault is repaired.
-- Bind the event key as $1; never concatenate user input.
UPDATE lead_events
SET status = 'failed',
    attempt_count = 0,
    last_error_code = 'RETRY_APPROVED',
    locked_at = NULL
WHERE idempotency_key = $1
  AND status IN ('failed', 'processing');

-- Unknown Slack outcomes are intentionally not auto-replayed. Verify manually,
-- then mark the effect completed or failed with a bound effect key ($1).
UPDATE workflow_effects
SET status = 'completed', completed_at = NOW(), last_error_code = NULL
WHERE effect_key = $1 AND status = 'unknown';

