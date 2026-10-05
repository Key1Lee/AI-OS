-- Two-row controlled unit-test example, separate from the fct_orders data tests.
select sum(case when status = 'complete' then amount else 0 end) as revenue
from {{ ref('unit_orders') }}
