select cast(customer_id as varchar) as customer_id, cast(email as varchar) as email
from {{ ref('customers_input') }}
