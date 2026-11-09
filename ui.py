from __future__ import annotations

import streamlit as st

from .analytics import order_frame, sales_summary
from .document_store import DocumentStore, create_document_store
from .sql_store import SQLStore


@st.cache_resource
def stores() -> tuple[SQLStore, DocumentStore]:
    return SQLStore(), create_document_store()


def run_app() -> None:
    st.set_page_config(page_title="ShopSphere", page_icon="🛍️", layout="wide")
    sql, mongo = stores()
    st.title("ShopSphere")
    st.caption("Hybrid multi-seller marketplace | INF2003 Database Systems | Group 63")
    if "user" not in st.session_state:
        st.session_state.user = None
    with st.sidebar:
        st.header("Account")
        if st.session_state.user:
            st.success(f"Signed in as {st.session_state.user['full_name']}")
            if st.button("Log out"):
                st.session_state.user = None
                st.rerun()
        else:
            login_tab, register_tab = st.tabs(["Log in", "Register"])
            with login_tab:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Log in"):
                    user = sql.authenticate(email, password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
            with register_tab:
                name = st.text_input("Full name")
                new_email = st.text_input("New email")
                new_password = st.text_input("New password", type="password")
                if st.button("Create account"):
                    try:
                        sql.register(new_email, name, new_password)
                        st.success("Account created. You can now log in.")
                    except Exception as exc:
                        st.error(str(exc))
    user = st.session_state.user
    if not user:
        st.info("Log in to manage your cart and orders, or browse the catalogue below.")
        _catalogue(sql, mongo, None)
        return
    pages = ["Catalogue", "Cart", "My orders"]
    pages.append("Profile")
    if user["role"] in {"seller", "admin"}:
        pages.append("Seller dashboard")
    if user["role"] == "admin":
        pages.append("Admin dashboard")
    page = st.sidebar.radio("Navigate", pages)
    if page == "Catalogue":
        _catalogue(sql, mongo, user)
    elif page == "Cart":
        _cart(sql, user)
    elif page == "My orders":
        _orders(sql, user)
    elif page == "Profile":
        _profile(sql, user)
    elif page == "Seller dashboard":
        _seller_dashboard(sql, user)
    else:
        _admin_dashboard(sql, mongo)


def _catalogue(sql: SQLStore, mongo: DocumentStore, user: dict | None) -> None:
    st.header("Product catalogue")
    left, middle, right = st.columns([2, 1, 1])
    with left:
        search = st.text_input("Search products")
    with middle:
        category = st.selectbox("Category", ["All", *sql.categories()])
    with right:
        sort = st.selectbox("Sort by", ["Newest", "Price: low to high", "Price: high to low", "Name"])
    products = sql.catalogue(search, category, sort)
    for product in products:
        with st.container(border=True):
            st.subheader(product["name"])
            st.write(product["description"])
            st.write(f"**${product['price']:.2f}** · {product['category_name']} · {product['store_name']} · {product['stock_quantity']} in stock")
            rating = mongo.average_rating(product["product_id"])
            st.caption(f"MongoDB average rating: {rating or 'No ratings yet'}")
            if st.button("View details", key=f"view-{product['product_id']}"):
                mongo.record_view(user["user_id"] if user else 0, product["product_id"])
                st.session_state.selected_product = product["product_id"]
            if user:
                qty = st.number_input("Quantity", min_value=1, max_value=max(1, product["stock_quantity"]),
                                      value=1, key=f"qty-{product['product_id']}")
                if st.button("Add to cart", key=f"cart-{product['product_id']}"):
                    try:
                        sql.set_cart_item(user["user_id"], product["product_id"], int(qty))
                        st.success("Cart updated.")
                    except ValueError as exc:
                        st.error(str(exc))
    selected = st.session_state.get("selected_product")
    if selected:
        _product_detail(sql, mongo, user, selected)


def _product_detail(sql: SQLStore, mongo: DocumentStore, user: dict | None, product_id: int) -> None:
    product = sql.product(product_id)
    if not product:
        return
    st.subheader(f"Details: {product['name']}")
    st.write(product["description"])
    st.write(f"Price: ${product['price']:.2f} | Stock: {product['stock_quantity']}")
    st.json(mongo.specifications.get(product_id, {"attributes": {"material": "Demo specification"}}))
    reviews = mongo.reviews_for(product_id)
    st.write(f"Average rating: {mongo.average_rating(product_id) or 'No ratings yet'}")
    for review in reviews:
        st.write(f"⭐ {review['rating']}/5 — {review['comment']}")
    if user:
        with st.form(f"review-{product_id}"):
            rating = st.slider("Rating", 1, 5, 5)
            comment = st.text_area("Review")
            if st.form_submit_button("Save review"):
                mongo.add_review(user["user_id"], product_id, rating, comment)
                st.success("Review saved.")
        own_review = mongo.review_for_user(user["user_id"], product_id)
        if own_review and st.button("Delete my review", key=f"delete-review-{product_id}"):
            mongo.delete_review(user["user_id"], product_id)
            st.success("Review deleted.")


def _cart(sql: SQLStore, user: dict) -> None:
    st.header("Your cart")
    cart = sql.cart(user["user_id"])
    if not cart:
        st.info("Your cart is empty.")
        return
    for item in cart:
        st.write(f"{item['name']} × {item['quantity']} — ${item['subtotal']:.2f}")
        quantity = st.number_input("Quantity", min_value=0, value=item["quantity"], key=f"edit-{item['product_id']}")
        if st.button("Update", key=f"update-{item['product_id']}"):
            try:
                sql.set_cart_item(user["user_id"], item["product_id"], int(quantity))
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    total = sum(item["subtotal"] for item in cart)
    st.metric("Total", f"${total:.2f}")
    if st.button("Place simulated order"):
        try:
            order_id = sql.checkout(user["user_id"])
            st.success(f"Order #{order_id} placed.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def _orders(sql: SQLStore, user: dict) -> None:
    st.header("Order history")
    frame = order_frame(sql, user["user_id"])
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _seller_dashboard(sql: SQLStore, user: dict) -> None:
    st.header("Seller dashboard")
    try:
        products = sql.seller_products(user["user_id"])
        orders = sql.seller_orders(user["user_id"])
    except PermissionError as exc:
        st.error(str(exc))
        return
    st.metric("Your products", len(products))
    st.metric("Your order lines", len(orders))
    st.dataframe(products, use_container_width=True, hide_index=True)
    if products:
        selected = st.selectbox("Update stock", products, format_func=lambda p: p["name"])
        quantity = st.number_input("New stock", min_value=0, value=int(selected["stock_quantity"]))
        if st.button("Save stock"):
            try:
                sql.update_inventory(user["user_id"], selected["product_id"], int(quantity))
                st.success("Inventory updated.")
            except (PermissionError, ValueError) as exc:
                st.error(str(exc))
    st.subheader("Orders containing your products")
    st.dataframe(orders, use_container_width=True, hide_index=True)


def _admin_dashboard(sql: SQLStore, mongo: DocumentStore) -> None:
    st.header("Admin dashboard")
    summary = sales_summary(sql)
    one, two, three = st.columns(3)
    one.metric("Total revenue", f"${summary['revenue']:.2f}")
    two.metric("Total orders", summary["orders"])
    three.metric("Product views", len(mongo.history))
    frame = order_frame(sql)
    if not frame.empty:
        st.bar_chart(frame.set_index("created_at")["total_amount"])
    st.subheader("Most viewed products")
    st.dataframe(mongo.top_viewed(), use_container_width=True)
    report = sql.analytics()
    st.subheader("Sales by category")
    st.dataframe(report["categories"], use_container_width=True, hide_index=True)
    st.subheader("Low-stock alerts")
    st.dataframe(report["low_stock"], use_container_width=True, hide_index=True)


def _profile(sql: SQLStore, user: dict) -> None:
    st.header("Profile")
    name = st.text_input("Full name", value=user["full_name"])
    email = st.text_input("Email", value=user["email"])
    if st.button("Save profile"):
        try:
            sql.update_profile(user["user_id"], name, email)
            st.session_state.user = {**user, "full_name": name.strip(), "email": email.strip().lower()}
            st.success("Profile updated.")
        except ValueError as exc:
            st.error(str(exc))
