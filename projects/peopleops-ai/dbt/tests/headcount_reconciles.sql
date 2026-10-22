select w.headcount from {{ ref('fct_workforce') }} w
where w.headcount != (select sum(headcount) from {{ ref('fct_department_headcount') }})
