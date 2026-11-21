import os
import uuid

import pytest
from PIL import Image

from shopsphere.db.mongodb_store import MongoDBStore
from shopsphere.document_store import DocumentStore
from shopsphere.scripts.import_olist import import_products, sample_order_reviews
from shopsphere.sql_store import SQLStore
from shopsphere.ui import _product_card_image


def make_store(tmp_path):
    return SQLStore(tmp_path / "test.db")


def test_login_cart_checkout_and_rollback(tmp_path):
    store = make_store(tmp_path)
    user = store.authenticate("customer@shopsphere.local", "Customer123!")
    assert user is not None
    product = store.catalogue()[0]
    store.set_cart_item(user["user_id"], product["product_id"], 1)
    order_id = store.checkout(user["user_id"])
    assert store.orders(user["user_id"])[0]["order_id"] == order_id
    with pytest.raises(ValueError, match="empty"):
        store.checkout(user["user_id"])


def test_document_crud_and_aggregation():
    store = DocumentStore()
    store.add_review(1, 10, 5, "Excellent")
    store.add_review(2, 10, 3, "Useful")
    assert store.average_rating(10) == 4.0
    assert store.aggregate_rating() == [{"product_id": 10, "average_rating": 4.0, "review_count": 2}]
    store.delete_review(1, 10)
    assert len(store.reviews_for(10)) == 1


def test_demo_reviews_seed_two_to_four_times_per_product_and_are_idempotent(tmp_path):
    products = make_store(tmp_path).catalogue()
    products.extend([
        {"product_id": 1001, "name": "Ceramic Mug"},
        {"product_id": 1002, "name": "Chino Shorts"},
    ])
    store = DocumentStore()
    color_variants = {
        product["product_id"]: ("Beige", "Blue")
        for product in products
        if product["name"] in {"Ceramic Mug", "Chino Shorts"}
    }

    store.seed_demo_reviews(products, color_variants)
    review_counts = {
        product["product_id"]: len(store.reviews_for(product["product_id"]))
        for product in products
    }

    assert all(2 <= count <= 4 for count in review_counts.values())
    assert all(review["is_demo"] and review["reviewer_name"] for review in store.reviews)
    for product in products[-2:]:
        assert {review["color"] for review in store.reviews_for(product["product_id"])} == {
            "Beige",
            "Blue",
        }
    initial_count = len(store.reviews)
    store.seed_demo_reviews(products)
    assert len(store.reviews) == initial_count

    product_id = products[0]["product_id"]
    store.add_review(100, product_id, 4, "Customer-submitted review")
    assert store.review_for_user(100, product_id)["is_demo"] is False


def test_demo_review_seed_updates_existing_samples_with_names_and_variants():
    store = DocumentStore()
    store.reviews.append({
        "user_id": -1,
        "product_id": 10,
        "rating": 5,
        "comment": "Old sample text",
        "is_demo": True,
    })

    store.seed_demo_reviews(
        [{"product_id": 10, "name": "Ceramic Mug"}],
        {10: ("Beige", "Blue")},
    )

    review = store.reviews_for(10)[0]
    assert review["reviewer_name"] == "Maya Chen"
    assert review["color"] == "Beige"
    assert "Ceramic Mug" in review["comment"]


def test_registration_validation_and_seller_ownership(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError):
        store.register("bad", "", "short")
    seller = store.authenticate("seller@shopsphere.local", "Seller123!")
    customer = store.authenticate("customer@shopsphere.local", "Customer123!")
    assert seller and customer
    product = store.seller_products(seller["user_id"])[0]
    with pytest.raises(PermissionError):
        store.update_inventory(customer["user_id"], product["product_id"], 2)
    with pytest.raises(ValueError):
        store.update_inventory(seller["user_id"], product["product_id"], -1)


def test_cart_quantity_and_low_stock_analytics(tmp_path):
    store = make_store(tmp_path)
    customer = store.authenticate("customer@shopsphere.local", "Customer123!")
    product = store.catalogue()[0]
    with pytest.raises(ValueError):
        store.set_cart_item(customer["user_id"], product["product_id"], 999)
    report = store.analytics()
    assert {"revenue", "categories", "low_stock"} == set(report)


def test_zero_inventory_is_reported_and_cannot_be_purchased(tmp_path):
    store = make_store(tmp_path)
    customer = store.authenticate("customer@shopsphere.local", "Customer123!")
    seller = store.authenticate("seller@shopsphere.local", "Seller123!")
    product = store.seller_products(seller["user_id"])[0]
    product_id = product["product_id"]

    store.set_cart_item(customer["user_id"], product_id, 1)
    store.update_inventory(seller["user_id"], product_id, 0)

    assert store.cart(customer["user_id"])[0]["stock_quantity"] == 0
    with pytest.raises(ValueError, match="Stock changed"):
        store.checkout(customer["user_id"])
    with pytest.raises(ValueError, match="exceeds available stock"):
        store.set_cart_item(customer["user_id"], product_id, 1)


def test_color_variants_stay_separate_in_cart_and_order(tmp_path):
    store = make_store(tmp_path)
    customer = store.authenticate("customer@shopsphere.local", "Customer123!")
    seller = store.authenticate("seller@shopsphere.local", "Seller123!")
    with store.connection() as conn:
        category_id = conn.execute(
            "SELECT category_id FROM categories WHERE name='Home & Living'"
        ).fetchone()[0]
    mug_id = store.create_product(
        seller["user_id"], category_id, "Ceramic Mug", "A ceramic mug.", 12.5, 10
    )

    store.set_cart_item(customer["user_id"], mug_id, 2, color="Beige")
    store.set_cart_item(customer["user_id"], mug_id, 1, color="Blue")

    cart = store.cart(customer["user_id"])
    assert {(item["color"], item["quantity"]) for item in cart} == {
        ("Beige", 2),
        ("Blue", 1),
    }
    with pytest.raises(ValueError, match="Choose a color"):
        store.set_cart_item(customer["user_id"], mug_id, 1)
    order_id = store.checkout(customer["user_id"])
    with store.connection() as conn:
        order_colors = conn.execute(
            "SELECT color, quantity FROM order_items WHERE order_id=?",
            (order_id,),
        ).fetchall()
    assert {(row["color"], row["quantity"]) for row in order_colors} == {
        ("Beige", 2),
        ("Blue", 1),
    }


def test_seller_can_save_product_photo_and_customer_cannot(tmp_path):
    store = make_store(tmp_path)
    seller = store.authenticate("seller@shopsphere.local", "Seller123!")
    customer = store.authenticate("customer@shopsphere.local", "Customer123!")
    product = store.seller_products(seller["user_id"])[0]

    filename = store.save_product_image(
        seller["user_id"], product["product_id"], b"test image bytes", "jpg"
    )

    assert filename == f"{product['product_id']}.jpg"
    image_path = store.product_image_path(filename)
    assert image_path is not None
    assert image_path.read_bytes() == b"test image bytes"
    with pytest.raises(PermissionError, match="Seller access required"):
        store.save_product_image(
            customer["user_id"], product["product_id"], b"other image", "jpg"
        )


def test_existing_database_is_migrated_for_product_photos(tmp_path):
    store = make_store(tmp_path)
    with store.connection() as conn:
        conn.execute("ALTER TABLE products DROP COLUMN image_filename")

    migrated_store = SQLStore(store.path)
    product = migrated_store.catalogue()[0]

    assert product["image_filename"] is None


def test_existing_database_is_migrated_for_product_sources(tmp_path):
    store = make_store(tmp_path)
    with store.connection() as conn:
        conn.execute("DROP INDEX idx_products_source")
        conn.execute("ALTER TABLE products DROP COLUMN source_name")
        conn.execute("ALTER TABLE products DROP COLUMN source_id")

    migrated_store = SQLStore(store.path)
    with migrated_store.connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(products)")}
        indexes = {row["name"] for row in conn.execute("PRAGMA index_list(products)")}

    assert {"source_name", "source_id"} <= columns
    assert "idx_products_source" in indexes


def test_olist_import_uses_source_price_and_zero_stock_and_is_idempotent(tmp_path):
    raw_dir = tmp_path / "olist"
    raw_dir.mkdir()
    (raw_dir / "olist_products_dataset.csv").write_text(
        "product_id,product_category_name,product_weight_g,product_length_cm,"
        "product_height_cm,product_width_cm\n"
        "product-a,home,100,10,5,4\n"
        "product-b,books,200,20,10,8\n",
        encoding="utf-8",
    )
    (raw_dir / "olist_order_items_dataset.csv").write_text(
        "product_id,price\nproduct-a,10.00\nproduct-a,14.00\nproduct-b,20.00\n",
        encoding="utf-8",
    )

    class RecordingMongoStore:
        def __init__(self):
            self.specifications = {}

        def set_specifications(self, product_id, attributes):
            self.specifications[product_id] = attributes

    store = make_store(tmp_path)
    mongo_store = RecordingMongoStore()

    assert import_products(store, mongo_store, raw_dir, limit=1) == 1
    with store.connection() as conn:
        first_import = conn.execute(
            "SELECT product_id, name FROM products WHERE source_name = 'Olist'"
        ).fetchone()
        imported_id = first_import["product_id"]
        conn.execute(
            "UPDATE products SET name = ?, description = ? WHERE product_id = ?",
            ("My chosen product name", "My product description", imported_id),
        )
    assert first_import["name"] == "Home Item 01"
    assert import_products(store, mongo_store, raw_dir, limit=1) == 1

    with store.connection() as conn:
        imported = conn.execute(
            """SELECT p.product_id, p.price, p.source_name, p.source_id, p.name,
                      p.description, i.quantity
               FROM products p JOIN inventory i USING(product_id)
               WHERE p.source_name = 'Olist'"""
        ).fetchone()
        source_count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE source_name = 'Olist'"
        ).fetchone()[0]

    assert source_count == 1
    assert imported["source_id"] == "product-a"
    assert imported["price"] == 12
    assert imported["quantity"] == 0
    assert imported["name"] == "My chosen product name"
    assert imported["description"] == "My product description"
    assert mongo_store.specifications[imported["product_id"]] == {
        "source": "Olist",
        "source_product_id": "product-a",
        "source_category": "home",
        "product_weight_g": 100,
        "product_length_cm": 10,
        "product_height_cm": 5,
        "product_width_cm": 4,
    }


def test_olist_review_import_sampling_is_repeatable_and_bounded(tmp_path):
    raw_dir = tmp_path / "olist"
    raw_dir.mkdir()
    (raw_dir / "olist_order_reviews_dataset.csv").write_text(
        "review_id,order_id,review_score\n"
        "review-a,order-a,5\nreview-b,order-b,4\nreview-c,order-c,3\n",
        encoding="utf-8",
    )

    first_sample = sample_order_reviews(raw_dir, limit=2)

    assert len(first_sample) == 2
    assert first_sample == sample_order_reviews(raw_dir, limit=2)
    assert sample_order_reviews(raw_dir, limit=0) == []


def test_mongodb_document_store_integration():
    uri = os.getenv("MONGODB_TEST_URI")
    if not uri:
        pytest.skip("Set MONGODB_TEST_URI to run the MongoDB integration test.")

    database_name = f"shopsphere_test_{uuid.uuid4().hex}"
    store = MongoDBStore(uri=uri, database_name=database_name)
    try:
        sample_products = [{"product_id": 11, "name": "Garden Tools Item 01"}]
        store.seed_demo_reviews(sample_products)
        seeded_samples = store.reviews_for(11)
        store.seed_demo_reviews(sample_products)

        store.record_view(1, 10)
        store.add_review(1, 10, 5, "MongoDB integration test")
        store.set_specifications(10, {"source": "test"})
        reviews = [
            {"review_id": "olist-1", "order_id": "order-1", "review_score": "4"},
            {"review_id": "olist-2", "order_id": "order-2", "review_score": "5"},
        ]
        imported = store.import_olist_reviews(reviews)
        store.import_olist_reviews(reviews)

        assert store.reviews_for(10)[0]["rating"] == 5
        assert store.average_rating(10) == 5.0
        assert 2 <= len(seeded_samples) <= 4
        assert len(store.reviews_for(11)) == len(seeded_samples)
        assert all(review["is_demo"] and review["reviewer_name"] for review in seeded_samples)
        assert store.browsing_history(1)[0]["product_id"] == 10
        assert store.specifications_for(10)["attributes"] == {"source": "test"}
        assert imported == 2
        assert store.olist_reviews.count_documents({}) == 2
        assert store.source_review_summary() == {
            "count": 2,
            "average_score": 4.5,
            "distribution": [
                {"rating": 4, "reviews": 1},
                {"rating": 5, "reviews": 1},
            ],
        }
    finally:
        store.client.drop_database(database_name)
        store.close()


@pytest.mark.parametrize(
    ("source_size", "letterbox_pixel"),
    [((1200, 400), (320, 10)), ((300, 900), (10, 240))],
)
def test_product_card_images_use_uniform_letterboxed_frames(
    tmp_path, source_size, letterbox_pixel
):
    source_path = tmp_path / "product.png"
    Image.new("RGB", source_size, "#ff0000").save(source_path)

    frame = _product_card_image(str(source_path), source_path.stat().st_mtime_ns)

    assert frame.size == (640, 480)
    assert frame.getpixel((320, 240)) == (255, 0, 0)
    assert frame.getpixel(letterbox_pixel) == (23, 33, 45)
    with Image.open(source_path) as source:
        assert source.size == source_size


def test_existing_cart_rows_are_migrated_for_color_variants(tmp_path):
    store = make_store(tmp_path)
    customer = store.authenticate("customer@shopsphere.local", "Customer123!")
    product = store.catalogue()[0]
    store.set_cart_item(customer["user_id"], product["product_id"], 2)

    with store.connection() as conn:
        conn.execute(
            """CREATE TABLE legacy_cart_items (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, product_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(product_id) REFERENCES products(product_id)
            )"""
        )
        conn.execute(
            """INSERT INTO legacy_cart_items(user_id, product_id, quantity, updated_at)
               SELECT user_id, product_id, quantity, updated_at FROM cart_items"""
        )
        conn.execute("DROP TABLE cart_items")
        conn.execute("ALTER TABLE legacy_cart_items RENAME TO cart_items")
        conn.execute("ALTER TABLE order_items DROP COLUMN color")

    migrated_store = SQLStore(store.path)

    assert migrated_store.cart(customer["user_id"])[0]["color"] == ""
    with migrated_store.connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(order_items)")}
    assert "color" in columns
