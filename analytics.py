from __future__ import annotations

import pandas as pd

from .sql_store import SQLStore


def order_frame(store: SQLStore, user_id: int | None = None) -> pd.DataFrame:
    return pd.DataFrame(store.orders(user_id))


def sales_summary(store: SQLStore) -> dict[str, float]:
    frame = order_frame(store)
    if frame.empty:
        return {"revenue": 0.0, "orders": 0}
    return {"revenue": float(frame["total_amount"].sum()), "orders": int(len(frame))}

