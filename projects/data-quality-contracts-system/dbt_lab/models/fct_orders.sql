-- Provider adapter over already-produced fixture rows. This is not a Modeling engine.
select
    cast(order_id as varchar) as order_id,
    cast(customer_id as varchar) as customer_id,
    cast(ordered_at as timestamptz) as ordered_at,
    cast(net_revenue as decimal(18,2)) as net_revenue,
    cast(status as varchar) as status,
    cast(payment_status as varchar) as payment_status,
    cast(shipped_at as timestamptz) as shipped_at,
    cast(description as varchar) as description,
    cast(currency as varchar) as currency
from {{ ref('fct_orders_input') }}
