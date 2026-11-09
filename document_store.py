from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class DocumentStore:
    """MongoDB-shaped operational store with an in-memory demo implementation."""

    def __init__(self) -> None:
        self.reviews: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.specifications: dict[int, dict[str, Any]] = {}

    def record_view(self, user_id: int, product_id: int) -> None:
        self.history.append({"user_id": user_id, "product_id": product_id,
                             "event_type": "view", "timestamp": datetime.now(timezone.utc)})

    def reviews_for(self, product_id: int) -> list[dict[str, Any]]:
        return [r for r in self.reviews if r["product_id"] == product_id]

    def average_rating(self, product_id: int) -> float:
        rows = self.reviews_for(product_id)
        return round(sum(r["rating"] for r in rows) / len(rows), 2) if rows else 0.0

    def add_review(self, user_id: int, product_id: int, rating: int, comment: str) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        self.reviews[:] = [r for r in self.reviews
                           if not (r["user_id"] == user_id and r["product_id"] == product_id)]
        self.reviews.append({"user_id": user_id, "product_id": product_id, "rating": rating,
                             "comment": comment.strip(), "timestamp": datetime.now(timezone.utc)})

    def delete_review(self, user_id: int, product_id: int) -> None:
        self.reviews[:] = [r for r in self.reviews
                           if not (r["user_id"] == user_id and r["product_id"] == product_id)]

    def review_for_user(self, user_id: int, product_id: int) -> dict[str, Any] | None:
        return next((r for r in self.reviews
                     if r["user_id"] == user_id and r["product_id"] == product_id), None)

    def browsing_history(self, user_id: int | None = None) -> list[dict[str, Any]]:
        rows = self.history if user_id is None else [
            item for item in self.history if item["user_id"] == user_id
        ]
        return sorted(rows, key=lambda item: item["timestamp"], reverse=True)

    def aggregate_rating(self, product_ids: list[int] | None = None) -> list[dict[str, Any]]:
        selected = self.reviews if product_ids is None else [
            item for item in self.reviews if item["product_id"] in product_ids
        ]
        grouped: dict[int, list[int]] = {}
        for item in selected:
            grouped.setdefault(item["product_id"], []).append(item["rating"])
        return [{"product_id": product_id, "average_rating": round(sum(ratings) / len(ratings), 2),
                 "review_count": len(ratings)}
                for product_id, ratings in grouped.items()]

    def set_specifications(self, product_id: int, attributes: dict[str, Any]) -> None:
        self.specifications[product_id] = {"product_id": product_id, "attributes": attributes,
                                           "updated_at": datetime.now(timezone.utc)}

    def top_viewed(self) -> list[tuple[int, int]]:
        counts: dict[int, int] = {}
        for event in self.history:
            counts[event["product_id"]] = counts.get(event["product_id"], 0) + 1
        return sorted(counts.items(), key=lambda item: item[1], reverse=True)


def create_document_store() -> DocumentStore:
    return DocumentStore()
