{{ config(meta={'quality_rule_id': 'completed_paid', 'blocking': true}) }}
select *
from {{ ref('fct_orders') }}
where status = 'completed' and (payment_status is null or payment_status <> 'paid')
