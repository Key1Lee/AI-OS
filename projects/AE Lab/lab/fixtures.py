from __future__ import annotations

from decimal import Decimal

def commerce(seed: int = 42, count: int = 1000) -> dict:
    """Stable arithmetic fixtures; no clock, external source, or random fault."""
    if count != 1000:
        raise ValueError("Phase 1 contract requires exactly 1,000 orders")
    customers = [{"customer_id": f"C{i:03d}", "name": f"Customer {i}"} for i in range(1, 21)]
    orders = [{"order_id": f"O{i:04d}", "customer_id": customers[(i - 1) % 20]["customer_id"],
               "status": "completed", "order_amount": f"{Decimal(1000 + (i * 37 + seed) % 9000) / 100:.2f}",
               "currency": "USD", "ordered_at": f"2026-10-02T{(i - 1) % 24:02d}:00:00+00:00"}
              for i in range(1, count + 1)]
    return {"seed": seed, "customers": customers, "orders": orders,
            "products": [{"product_id": "P001", "name": "Lab item"}],
            "order_items": [{"order_id": o["order_id"], "product_id": "P001", "quantity": 1,
                             "item_amount": o["order_amount"]} for o in orders],
            "payments": [{"payment_id": f"PAY{i:04d}", "order_id": o["order_id"],
                          "amount": o["order_amount"], "status": "settled"} for i, o in enumerate(orders, 1)],
            "sessions": [{"session_id": f"S{i:03d}", "customer_id": c["customer_id"]} for i, c in enumerate(customers, 1)],
            "events": [{"event_id": f"E{i:04d}", "order_id": o["order_id"], "type": "order_completed"}
                       for i, o in enumerate(orders, 1)]}

def revenue(orders: list[dict]) -> str:
    return f"{sum((Decimal(o['order_amount']) for o in orders if o['status'] == 'completed'), Decimal(0)):.2f}"

def key_batches(orders: list[dict], limit: int = 180) -> list[list[dict]]:
    """Keep every occurrence of a key together; independent of input row order."""
    groups: dict[str, list[dict]] = {}
    for order in orders:
        groups.setdefault(order["order_id"], []).append(order)
    batches, batch = [], []
    for key in sorted(groups):
        group = groups[key]
        if len(group) > limit:
            raise ValueError(f"{key}: key group exceeds native bounded dataset limit")
        if len(batch) + len(group) > limit:
            batches.append(batch)
            batch = []
        batch.extend(group)
    if batch:
        batches.append(batch)
    return batches
