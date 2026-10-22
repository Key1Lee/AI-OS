-- Only the fields needed for analytics cross this boundary.
select employee_id, department, status, hire_date, termination_date, manager_id
from {{ source('application', 'employees') }}
