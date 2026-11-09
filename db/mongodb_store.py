"""Optional PyMongo operational store used by database-service deployments."""
from datetime import datetime, timezone
from typing import Any

from ..config import settings


class MongoDBStore:
    def __init__(self) -> None:
        try:
            from pymongo import MongoClient
        except ImportError as exc:
            raise RuntimeError("MongoDB mode requires pymongo.") from exc
        self.client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
        self.database = self.client[settings.mongodb_database]
        self.reviews = self.database["Reviews"]
        self.history = self.database["BrowsingHistory"]
        self.specifications = self.database["ProductSpecifications"]

    def record_view(self, user_id: int, product_id: int) -> None:
        self.history.insert_one({
            "user_id": user_id, "product_id": product_id, "event_type": "view",
            "timestamp": datetime.now(timezone.utc),
        })

    def add_review(self, user_id: int, product_id: int, rating: int, comment: str) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        self.reviews.update_one(
            {"user_id": user_id, "product_id": product_id},
            {"$set": {"rating": rating, "comment": comment.strip(),
                      "updated_at": datetime.now(timezone.utc)},
             "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    def average_rating(self, product_id: int) -> float:
        result = list(self.reviews.aggregate([
            {"$match": {"product_id": product_id}},
            {"$group": {"_id": "$product_id", "average": {"$avg": "$rating"}}},
        ]))
        return round(float(result[0]["average"]), 2) if result else 0.0

    def top_viewed(self) -> list[dict[str, Any]]:
        return list(self.history.aggregate([
            {"$group": {"_id": "$product_id", "views": {"$sum": 1}}},
            {"$sort": {"views": -1}},
            {"$project": {"_id": 0, "product_id": "$_id", "views": 1}},
        ]))

    def close(self) -> None:
        self.client.close()
