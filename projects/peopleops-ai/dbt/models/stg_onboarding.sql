select task_id, employee_id, kind, status, due_date
from {{ source('application', 'onboarding_tasks') }}
