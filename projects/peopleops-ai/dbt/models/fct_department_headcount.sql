select department, count(*) as headcount
from {{ ref('stg_employees') }}
where status in ('active', 'leave') and hire_date <= '{{ var("as_of") }}'
group by department
