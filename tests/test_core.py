import pytest

from shopsphere.document_store import DocumentStore
from shopsphere.sql_store import SQLStore


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
