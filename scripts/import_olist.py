"""Import a representative Olist catalog and its order-level review data."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from random import Random
from typing import Any, Iterator

from shopsphere.db.mongodb_store import MongoDBStore
from shopsphere.sql_store import SQLStore

SOURCE_NAME = "Olist"
PRODUCT_COLUMNS = {"product_id", "product_category_name"}
ITEM_COLUMNS = {"product_id", "price"}
REVIEW_COLUMNS = {"review_id", "order_id", "review_score"}
SPECIFICATION_COLUMNS = (
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
)
TRANSLATION_COLUMNS = {"product_category_name", "product_category_name_english"}


def iter_csv_rows(path: Path, required_columns: set[str]) -> Iterator[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required Olist CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns - set(reader.fieldnames or ())
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{path.name} is missing required columns: {missing}")
        for row in reader:
            yield {key: (value or "").strip() for key, value in row.items() if key}


def average_sold_prices(raw_dir: Path) -> dict[str, tuple[Decimal, int]]:
    totals: dict[str, tuple[Decimal, int]] = {}
    items_path = raw_dir / "olist_order_items_dataset.csv"
    for row in iter_csv_rows(items_path, ITEM_COLUMNS):
        product_id = row["product_id"]
        if not product_id:
            continue
        try:
            price = Decimal(row["price"])
        except InvalidOperation as error:
            raise ValueError(f"Invalid price for Olist product {product_id!r}") from error
        if not price.is_finite() or price < 0:
            raise ValueError(f"Invalid price for Olist product {product_id!r}")
        total, count = totals.get(product_id, (Decimal(0), 0))
        totals[product_id] = (total + price, count + 1)
    return totals


def _category_translations(raw_dir: Path) -> dict[str, str]:
    path = raw_dir / "product_category_name_translation.csv"
    if not path.is_file():
        return {}
    return {
        row["product_category_name"]: row["product_category_name_english"]
        for row in iter_csv_rows(path, TRANSLATION_COLUMNS)
        if row["product_category_name"] and row["product_category_name_english"]
    }


def _numeric_attributes(row: dict[str, str]) -> dict[str, int | float]:
    attributes: dict[str, int | float] = {}
    for column in SPECIFICATION_COLUMNS:
        value = row.get(column, "")
        if not value:
            continue
        try:
            number = Decimal(value)
        except InvalidOperation as error:
            raise ValueError(f"Invalid {column} value for Olist product {row['product_id']!r}") from error
        if not number.is_finite():
            raise ValueError(f"Invalid {column} value for Olist product {row['product_id']!r}")
        attributes[column] = int(number) if number == number.to_integral_value() else float(number)
    return attributes


def _source_products(raw_dir: Path, limit: int) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("The product limit must be at least 1")

    prices = average_sold_prices(raw_dir)
    translations = _category_translations(raw_dir)
    products_path = raw_dir / "olist_products_dataset.csv"
    products = []
    for row in iter_csv_rows(products_path, PRODUCT_COLUMNS):
        product_id = row["product_id"]
        if not product_id or product_id not in prices:
            continue
        total, count = prices[product_id]
        source_category = row["product_category_name"] or "uncategorized"
        category = translations.get(source_category, source_category)
        category = category.replace("_", " ").strip().title()
        products.append(
            {
                "source_id": product_id,
                "category": category,
                "source_category": source_category,
                "average_price": (total / count).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "item_count": count,
                "attributes": _numeric_attributes(row),
            }
        )
    products.sort(key=lambda product: (-product["item_count"], product["source_id"]))
    category_numbers: dict[str, int] = {}
    for product in products:
        category = product["category"]
        category_numbers[category] = category_numbers.get(category, 0) + 1
        product["name"] = f"{category} Item {category_numbers[category]:02d}"
    return products[:limit]


def import_products(
    sql_store: SQLStore,
    mongo_store: MongoDBStore,
    raw_dir: Path,
    limit: int = 100,
) -> int:
    products = _source_products(raw_dir, limit)
    if not products:
        raise ValueError("No matching Olist products and order items were found")

    specs_to_save: list[tuple[int, dict[str, Any]]] = []
    with sql_store.connection() as conn:
        seller = conn.execute("SELECT seller_id FROM sellers ORDER BY seller_id LIMIT 1").fetchone()
        if seller is None:
            raise RuntimeError("Cannot import Olist products: no seller exists in the SQL database")
        seller_id = seller["seller_id"]

        conn.execute("BEGIN")
        try:
            for product in products:
                category_name = product["category"]
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                    (category_name,),
                )
                category = conn.execute(
                    "SELECT category_id FROM categories WHERE name = ?",
                    (category_name,),
                ).fetchone()
                if category is None:
                    raise RuntimeError(f"Failed to create Olist category {category_name!r}")

                source_id = product["source_id"]
                name = product["name"]
                description = (
                    f"Category-based placeholder in {category_name}. Olist does not identify "
                    "this exact item or provide its retail description; replace this text "
                    "with your own description."
                )
                existing = conn.execute(
                    """SELECT product_id, name FROM products
                       WHERE source_name = ? AND source_id = ?""",
                    (SOURCE_NAME, source_id),
                ).fetchone()
                if existing is None:
                    cursor = conn.execute(
                        """INSERT INTO products
                           (seller_id, category_id, name, description, price, is_active, source_name, source_id)
                           VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                        (
                            seller_id,
                            category["category_id"],
                            name,
                            description,
                            str(product["average_price"]),
                            SOURCE_NAME,
                            source_id,
                        ),
                    )
                    product_id = cursor.lastrowid
                else:
                    product_id = existing["product_id"]
                    conn.execute(
                        "UPDATE products SET category_id = ?, price = ? WHERE product_id = ?",
                        (category["category_id"], str(product["average_price"]), product_id),
                    )
                    if existing["name"] == f"Olist product {source_id}":
                        conn.execute(
                            "UPDATE products SET name = ? WHERE product_id = ?",
                            (name, product_id),
                        )

                conn.execute(
                    "INSERT OR IGNORE INTO inventory (product_id, quantity) VALUES (?, 0)",
                    (product_id,),
                )
                specs_to_save.append(
                    (
                        product_id,
                        {
                            "source": SOURCE_NAME,
                            "source_product_id": source_id,
                            "source_category": product["source_category"],
                            **product["attributes"],
                        },
                    )
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    for product_id, specifications in specs_to_save:
        mongo_store.set_specifications(product_id, specifications)
    return len(products)


def sample_order_reviews(raw_dir: Path, limit: int, seed: int = 2026) -> list[dict[str, str]]:
    if limit < 0:
        raise ValueError("The review limit cannot be negative")
    if limit == 0:
        return []

    reviews_path = raw_dir / "olist_order_reviews_dataset.csv"
    rng = Random(seed)
    sample: list[dict[str, str]] = []
    seen = 0
    for row in iter_csv_rows(reviews_path, REVIEW_COLUMNS):
        if len(sample) < limit:
            sample.append(row)
        else:
            replacement = rng.randrange(seen + 1)
            if replacement < limit:
                sample[replacement] = row
        seen += 1
    return sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/olist"))
    parser.add_argument("--sqlite", type=Path, default=Path("data/shopsphere.db"))
    parser.add_argument("--limit-products", type=int, default=100)
    parser.add_argument("--limit-reviews", type=int, default=500)
    args = parser.parse_args()
    if args.limit_reviews < 0:
        parser.error("--limit-reviews cannot be negative")

    mongo_store = MongoDBStore()
    try:
        sql_store = SQLStore(args.sqlite)
        product_count = import_products(sql_store, mongo_store, args.data_dir, args.limit_products)
        reviews = sample_order_reviews(args.data_dir, args.limit_reviews)
        review_count = mongo_store.import_olist_reviews(reviews)
        print(f"Imported or updated {product_count} Olist products in SQLite and MongoDB specifications.")
        print(f"Imported {review_count} Olist order-level reviews into MongoDB.")
        print("Imported Olist products have zero starting inventory; Olist reviews are not ShopSphere reviews.")
    finally:
        mongo_store.close()


if __name__ == "__main__":
    main()
