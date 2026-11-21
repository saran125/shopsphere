"""Optional PyMongo operational store used by database-service deployments."""
from datetime import datetime, timezone
from typing import Any, Iterable

from ..config import settings
from ..document_store import DEMO_REVIEW_TEMPLATES

DEMO_USER_ID_BASE = 9_000_000_000


class MongoDBStore:
    def __init__(
        self,
        uri: str | None = None,
        database_name: str | None = None,
        server_selection_timeout_ms: int = 3000,
    ) -> None:
        try:
            from pymongo import ASCENDING, DESCENDING, MongoClient
            from pymongo.errors import PyMongoError
        except ImportError as exc:
            raise RuntimeError("MongoDB mode requires pymongo.") from exc
        self.client = MongoClient(
            uri or settings.mongodb_uri,
            serverSelectionTimeoutMS=server_selection_timeout_ms,
        )
        self.database = self.client[database_name or settings.mongodb_database]
        self.reviews = self.database["Reviews"]
        self.history = self.database["BrowsingHistory"]
        self.specifications = self.database["ProductSpecifications"]
        self.olist_reviews = self.database["OlistOrderReviews"]
        try:
            self.client.admin.command("ping")
            self.reviews.create_index(
                [("product_id", ASCENDING), ("user_id", ASCENDING)],
                unique=True,
                name="unique_product_user_review",
            )
            self.history.create_index(
                [("user_id", ASCENDING), ("timestamp", DESCENDING)],
                name="history_by_user_time",
            )
            self.history.create_index(
                [("product_id", ASCENDING), ("event_type", ASCENDING)],
                name="history_by_product_type",
            )
            self.specifications.create_index(
                [("product_id", ASCENDING)],
                unique=True,
                name="unique_product_specifications",
            )
            self.olist_reviews.create_index(
                [("review_id", ASCENDING)],
                unique=True,
                name="unique_olist_review",
            )
        except PyMongoError as exc:
            self.client.close()
            raise RuntimeError(
                "Could not connect to MongoDB or initialize ShopSphere collections."
            ) from exc

    def seed_demo_reviews(
        self,
        products: list[dict[str, Any]],
        variants_by_product: dict[int, tuple[str, ...]] | None = None,
    ) -> None:
        from pymongo import UpdateOne

        variants_by_product = variants_by_product or {}
        operations = []
        now = datetime.now(timezone.utc)
        for product in products:
            product_id = int(product["product_id"])
            variants = variants_by_product.get(product_id, ())
            review_count = 2 + product_id % 3
            for index, (rating, reviewer_name, template) in enumerate(
                DEMO_REVIEW_TEMPLATES[:review_count], start=1
            ):
                user_id = DEMO_USER_ID_BASE + index
                document = {
                    "user_id": user_id,
                    "product_id": product_id,
                    "rating": rating,
                    "reviewer_name": reviewer_name,
                    "comment": template.format(name=product["name"]),
                    "color": variants[(index - 1) % len(variants)] if variants else "",
                    "is_demo": True,
                    "updated_at": now,
                }
                operations.append(
                    UpdateOne(
                        {"user_id": user_id, "product_id": product_id},
                        {
                            "$set": document,
                            "$setOnInsert": {"created_at": now},
                        },
                        upsert=True,
                    )
                )
        if operations:
            self.reviews.bulk_write(operations, ordered=False)

    def record_view(self, user_id: int, product_id: int) -> None:
        self.history.insert_one({
            "user_id": user_id, "product_id": product_id, "event_type": "view",
            "timestamp": datetime.now(timezone.utc),
        })

    def reviews_for(self, product_id: int) -> list[dict[str, Any]]:
        return list(self.reviews.find(
            {"product_id": product_id},
            {"_id": 0},
        ).sort("created_at", 1))

    def add_review(self, user_id: int, product_id: int, rating: int, comment: str) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        now = datetime.now(timezone.utc)
        self.reviews.update_one(
            {"user_id": user_id, "product_id": product_id},
            {"$set": {"rating": rating, "comment": comment.strip(),
                      "updated_at": now, "is_demo": False},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    def delete_review(self, user_id: int, product_id: int) -> None:
        self.reviews.delete_one({"user_id": user_id, "product_id": product_id})

    def review_for_user(self, user_id: int, product_id: int) -> dict[str, Any] | None:
        return self.reviews.find_one(
            {"user_id": user_id, "product_id": product_id},
            {"_id": 0},
        )

    def average_rating(self, product_id: int) -> float:
        result = list(self.reviews.aggregate([
            {"$match": {"product_id": product_id}},
            {"$group": {"_id": "$product_id", "average": {"$avg": "$rating"}}},
        ]))
        return round(float(result[0]["average"]), 2) if result else 0.0

    def aggregate_rating(
        self, product_ids: list[int] | None = None
    ) -> list[dict[str, Any]]:
        match = {} if product_ids is None else {"product_id": {"$in": product_ids}}
        return list(self.reviews.aggregate([
            {"$match": match},
            {"$group": {
                "_id": "$product_id",
                "average_rating": {"$avg": "$rating"},
                "review_count": {"$sum": 1},
            }},
            {"$project": {
                "_id": 0,
                "product_id": "$_id",
                "average_rating": {"$round": ["$average_rating", 2]},
                "review_count": 1,
            }},
        ]))

    def browsing_history(self, user_id: int | None = None) -> list[dict[str, Any]]:
        query = {} if user_id is None else {"user_id": user_id}
        return list(self.history.find(query, {"_id": 0}).sort("timestamp", -1))

    def history_count(self) -> int:
        return self.history.count_documents({})

    def top_viewed(self) -> list[dict[str, int]]:
        return list(self.history.aggregate([
            {"$group": {"_id": "$product_id", "views": {"$sum": 1}}},
            {"$sort": {"views": -1}},
            {"$project": {"_id": 0, "product_id": "$_id", "views": 1}},
        ]))

    def specifications_for(self, product_id: int) -> dict[str, Any] | None:
        return self.specifications.find_one({"product_id": product_id}, {"_id": 0})

    def set_specifications(self, product_id: int, attributes: dict[str, Any]) -> None:
        self.specifications.update_one(
            {"product_id": product_id},
            {"$set": {
                "attributes": attributes,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    def import_olist_reviews(self, rows: Iterable[dict[str, str]]) -> int:
        from pymongo import UpdateOne

        operations = []
        imported = 0
        for row in rows:
            review_id = row.get("review_id", "").strip()
            if not review_id:
                continue
            try:
                rating = int(row["review_score"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Olist review {review_id} has an invalid score.") from exc
            if not 1 <= rating <= 5:
                raise ValueError(f"Olist review {review_id} has a score outside 1–5.")
            document = {
                "review_id": review_id,
                "order_id": row.get("order_id", "").strip(),
                "review_score": rating,
                "review_comment_title": row.get("review_comment_title", "").strip(),
                "review_comment_message": row.get("review_comment_message", "").strip(),
                "review_creation_date": row.get("review_creation_date", "").strip(),
                "review_answer_timestamp": row.get("review_answer_timestamp", "").strip(),
                "source": "Olist",
            }
            operations.append(
                UpdateOne({"review_id": review_id}, {"$set": document}, upsert=True)
            )
            if len(operations) == 500:
                self.olist_reviews.bulk_write(operations, ordered=False)
                imported += len(operations)
                operations.clear()
        if operations:
            self.olist_reviews.bulk_write(operations, ordered=False)
            imported += len(operations)
        return imported

    def source_review_summary(self) -> dict[str, Any] | None:
        results = list(self.olist_reviews.aggregate([
            {"$facet": {
                "scores": [
                    {"$group": {"_id": "$review_score", "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
                "summary": [
                    {"$group": {
                        "_id": None,
                        "count": {"$sum": 1},
                        "average_score": {"$avg": "$review_score"},
                    }},
                ],
            }},
        ]))
        if not results or not results[0]["summary"]:
            return None
        summary = results[0]["summary"][0]
        return {
            "count": int(summary["count"]),
            "average_score": round(float(summary["average_score"]), 2),
            "distribution": [
                {"rating": int(row["_id"]), "reviews": int(row["count"])}
                for row in results[0]["scores"]
            ],
        }

    def close(self) -> None:
        self.client.close()
