-- Event counts and a running total introduce CTEs and window functions.
-- Months with no events are omitted. This is not a daily historical snapshot.
with events as (
    select substr(hire_date,1,7) as month, 1 as hires, 0 as departures
    from {{ ref('stg_employees') }} where status != 'prehire' and hire_date <= '{{ var("as_of") }}'
    union all
    select substr(termination_date,1,7), 0, 1
    from {{ ref('stg_employees') }} where termination_date <= '{{ var("as_of") }}'
), monthly as (
    select month, sum(hires) as hires, sum(departures) as departures
    from events group by month
)
select month, hires, departures,
    sum(hires-departures) over (order by month rows between unbounded preceding and current row) as closing_headcount
from monthly
