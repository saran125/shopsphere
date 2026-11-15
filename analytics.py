from __future__ import annotations

from typing import Any

from .sql_store import SQLStore


def order_frame(store: SQLStore, user_id: int | None = None) -> list[dict[str, Any]]:
    return store.orders(user_id)


def sales_summary(store: SQLStore) -> dict[str, float | int]:
    orders = order_frame(store)
    if not orders:
        return {"revenue": 0.0, "orders": 0}
    return {
        "revenue": sum(float(order["total_amount"]) for order in orders),
        "orders": len(orders),
    }

