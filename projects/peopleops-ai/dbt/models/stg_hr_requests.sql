-- Ticket descriptions, employee names, emails, and salaries are excluded.
select request_id, employee_id, category, team, status, priority, created_at, resolved_at
from {{ source('application', 'hr_requests') }}
