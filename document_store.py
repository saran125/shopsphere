from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol


DEMO_REVIEW_TEMPLATES = (
    (
        5,
        "Maya Chen",
        "Really happy with the quality of {name}. It matches the listing and feels worth the price.",
    ),
    (
        4,
        "Ethan Lee",
        "The {name} is a good everyday choice. It arrived as described and fits what I needed.",
    ),
    (
        5,
        "Aisha Rahman",
        "Great value for money. The {name} looks even better in person than I expected.",
    ),
    (
        3,
        "Lucas Tan",
        "A decent {name} for the price. It meets the basics, though I hoped it would feel a little more premium.",
    ),
)


class DocumentBackend(Protocol):
    def seed_demo_reviews(
        self,
        products: list[dict[str, Any]],
        variants_by_product: dict[int, tuple[str, ...]] | None = None,
    ) -> None: ...

    def record_view(self, user_id: int, product_id: int) -> None: ...

    def reviews_for(self, product_id: int) -> list[dict[str, Any]]: ...

    def average_rating(self, product_id: int) -> float: ...

    def add_review(self, user_id: int, product_id: int, rating: int, comment: str) -> None: ...

    def delete_review(self, user_id: int, product_id: int) -> None: ...

    def review_for_user(self, user_id: int, product_id: int) -> dict[str, Any] | None: ...

    def specifications_for(self, product_id: int) -> dict[str, Any] | None: ...

    def set_specifications(self, product_id: int, attributes: dict[str, Any]) -> None: ...

    def history_count(self) -> int: ...

    def top_viewed(self) -> list[dict[str, int]]: ...

    def source_review_summary(self) -> dict[str, Any] | None: ...


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

    def seed_demo_reviews(
        self,
        products: list[dict[str, Any]],
        variants_by_product: dict[int, tuple[str, ...]] | None = None,
    ) -> None:
        seeded_reviews: dict[int, list[dict[str, Any]]] = {}
        for review in self.reviews:
            if review.get("is_demo"):
                seeded_reviews.setdefault(review["product_id"], []).append(review)
        variants_by_product = variants_by_product or {}
        for product in products:
            product_id = int(product["product_id"])
            variants = variants_by_product.get(product_id, ())
            existing_reviews = seeded_reviews.get(product_id, [])
            if existing_reviews:
                for index, review in enumerate(existing_reviews):
                    rating, reviewer_name, template = DEMO_REVIEW_TEMPLATES[
                        index % len(DEMO_REVIEW_TEMPLATES)
                    ]
                    review["rating"] = rating
                    review["reviewer_name"] = reviewer_name
                    review["comment"] = template.format(name=product["name"])
                    review["color"] = variants[index % len(variants)] if variants else ""
                continue
            review_count = 2 + product_id % 3
            for index, (rating, reviewer_name, template) in enumerate(
                DEMO_REVIEW_TEMPLATES[:review_count], start=1
            ):
                self.reviews.append({
                    "user_id": -index,
                    "product_id": product_id,
                    "rating": rating,
                    "reviewer_name": reviewer_name,
                    "comment": template.format(name=product["name"]),
                    "color": variants[(index - 1) % len(variants)] if variants else "",
                    "timestamp": datetime.now(timezone.utc),
                    "is_demo": True,
                })

    def average_rating(self, product_id: int) -> float:
        rows = self.reviews_for(product_id)
        return round(sum(r["rating"] for r in rows) / len(rows), 2) if rows else 0.0

    def add_review(self, user_id: int, product_id: int, rating: int, comment: str) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        self.reviews[:] = [r for r in self.reviews
                           if not (r["user_id"] == user_id and r["product_id"] == product_id)]
        self.reviews.append({"user_id": user_id, "product_id": product_id, "rating": rating,
                             "comment": comment.strip(), "timestamp": datetime.now(timezone.utc),
                             "is_demo": False})

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

    def specifications_for(self, product_id: int) -> dict[str, Any] | None:
        return self.specifications.get(product_id)

    def history_count(self) -> int:
        return len(self.history)

    def top_viewed(self) -> list[dict[str, int]]:
        counts: dict[int, int] = {}
        for event in self.history:
            counts[event["product_id"]] = counts.get(event["product_id"], 0) + 1
        return [
            {"product_id": product_id, "views": views}
            for product_id, views in sorted(
                counts.items(), key=lambda item: item[1], reverse=True
            )
        ]

    def source_review_summary(self) -> dict[str, Any] | None:
        return None


def create_document_store() -> DocumentStore:
    return DocumentStore()
