select employee_id,kind from {{ ref('stg_onboarding') }}
group by employee_id,kind having count(*) > 1
