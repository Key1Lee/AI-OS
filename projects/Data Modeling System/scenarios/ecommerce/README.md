# E-commerce revenue foundations

All data is synthetic. The JSON fixtures are canonical and packaged for standalone use.
The expected JSON is a separately hand-calculated oracle, not generated from reference SQL.

O1's latest version is USD 100.00; O2 is USD 50.00; O3 is USD 75.00.
O4 is cancelled and must be excluded. **Gross completed-order revenue = USD 225.00.**
It is not net revenue (a USD 25.00 return exists) or the sum of all payment attempts.

O1 has two items. Joining orders to items repeats its USD 100.00 order amount, so
four joined rows sum to USD 325.00. Aggregate items to order grain before attaching
them to an order fact. SUM(DISTINCT order_amount) is not a general repair: different
orders can have equal amounts.

Raw orderId alone is not unique. The raw key is (orderId, sourceVersion); choose
latest updatedAt, then sourceVersion, before declaring staging's one-order grain.
Contradictory records tied on both ordering fields require a producer decision;
the engine does not silently choose between them.
