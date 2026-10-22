select employee_id from {{ ref('stg_employees') }}
where termination_date < hire_date
   or (status='terminated' and termination_date is null)
   or (status!='terminated' and termination_date is not null)
