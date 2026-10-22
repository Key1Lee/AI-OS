with employee_counts as (
    select
        sum(case when status in ('active', 'leave') and hire_date <= '{{ var("as_of") }}' then 1 else 0 end) as headcount,
        sum(case when hire_date between date('{{ var("as_of") }}','-29 days') and '{{ var("as_of") }}'
            and status != 'prehire' then 1 else 0 end) as new_hires_30d,
        sum(case when termination_date between date('{{ var("as_of") }}','-29 days') and '{{ var("as_of") }}' then 1 else 0 end) as departures_30d
    from {{ ref('stg_employees') }}
), request_counts as (
    select count(*) as unresolved_requests from {{ ref('stg_hr_requests') }} where status != 'resolved'
), onboarding_counts as (
    select count(*) as total_tasks, coalesce(sum(status='completed'),0) as completed_tasks
    from {{ ref('stg_onboarding') }}
)
select '{{ var("as_of") }}' as as_of, e.*, r.*, o.*,
    round(100.0 * o.completed_tasks / nullif(o.total_tasks,0),1) as onboarding_completion_pct
from employee_counts e cross join request_counts r cross join onboarding_counts o
