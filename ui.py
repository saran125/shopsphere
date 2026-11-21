from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Callable

import streamlit as st
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from .analytics import order_frame, sales_summary
from .config import settings
from .document_store import DocumentBackend, create_document_store
from .sql_store import SQLStore, product_color_options


@st.cache_resource
def stores() -> tuple[SQLStore, DocumentBackend]:
    if settings.mode not in {"demo", "mongodb"}:
        raise ValueError("APP_MODE must be either 'demo' or 'mongodb'.")
    sql = SQLStore()
    if settings.mode == "mongodb":
        from .db.mongodb_store import MongoDBStore

        documents: DocumentBackend = MongoDBStore()
    else:
        documents = create_document_store()
    products = sql.catalogue()
    documents.seed_demo_reviews(
        products,
        {
            product["product_id"]: product_color_options(product["name"])
            for product in products
        },
    )
    return sql, documents


@st.cache_data(show_spinner=False)
def _product_card_image(image_path: str, modified_ns: int) -> Image.Image:
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((640, 480))
    frame = Image.new("RGB", (640, 480), "#17212D")
    frame.paste(image, ((640 - image.width) // 2, (480 - image.height) // 2))
    return frame


@st.cache_data(show_spinner=False)
def _product_card_placeholder() -> Image.Image:
    frame = Image.new("RGB", (640, 480), "#17212D")
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((258, 160, 382, 340), radius=20, outline="#34495A", width=8)
    draw.arc((287, 112, 353, 208), start=180, end=360, fill="#34495A", width=8)
    return frame


def run_app() -> None:
    st.set_page_config(page_title="ShopSphere", page_icon="🛍️", layout="wide")
    st.logo(str(Path(__file__).parent / "assets" / "shopsphere-logo.svg"), size="large")
    sql, mongo = stores()
    st.title("ShopSphere")
    st.caption("Thoughtful finds from independent sellers.")
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

    def open_product(product_id: int) -> None:
        st.session_state["selected_product_id"] = product_id
        st.switch_page(product_page)

    shop_page = st.Page(
        lambda: _catalogue(sql, mongo, user, open_product, cart_page),
        title="Shop",
        url_path="shop",
        icon=":material/storefront:",
        help="Browse products, filter the catalogue, and open a product's full details.",
    )
    cart_page = st.Page(
        lambda: _cart(sql, user, shop_page, orders_page),
        title="Cart",
        url_path="cart",
        icon=":material/shopping_cart:",
        help="Review, update, and place your order from one page.",
    )
    orders_page = st.Page(
        lambda: _orders(sql, user),
        title="Orders",
        url_path="orders",
        icon=":material/receipt_long:",
        help="View orders associated with your account.",
    )
    profile_page = st.Page(
        lambda: _profile(sql, user),
        title="Profile",
        url_path="profile",
        icon=":material/person:",
        help="Update the name and email address on your account.",
    )
    product_page = st.Page(
        lambda: _render_product_page(sql, mongo, user, shop_page, cart_page),
        title="Product details",
        url_path="product",
        icon=":material/visibility:",
        visibility="hidden",
        help="View an individual product, its description, reviews, and purchase options.",
    )

    pages = [shop_page, product_page]
    if user:
        pages.extend([cart_page, orders_page, profile_page])
        if user["role"] in {"seller", "admin"}:
            pages.append(
                st.Page(
                    lambda: _seller_dashboard(sql, user),
                    title="Seller dashboard",
                    url_path="seller",
                    icon=":material/inventory_2:",
                    help="Manage your products, stock, photos, and seller orders.",
                )
            )
        if user["role"] == "admin":
            pages.append(
                st.Page(
                    lambda: _admin_dashboard(sql, mongo),
                    title="Admin dashboard",
                    url_path="admin",
                    icon=":material/admin_panel_settings:",
                    help="Review marketplace activity, revenue, and low-stock products.",
                )
            )
    st.navigation(pages, position="top").run()


def _catalogue(
    sql: SQLStore,
    mongo: DocumentBackend,
    user: dict | None,
    open_product: Callable[[int], None],
    cart_page,
) -> None:
    if not user:
        st.info("Log in to manage your cart and orders, or browse the catalogue below.")
    st.header("Browse the collection")
    st.caption("Explore the latest products, compare prices, and find something you love.")
    left, middle, right = st.columns([2, 1, 1])
    with left:
        search = st.text_input("Search products", type="search")
    with middle:
        category = st.selectbox("Category", ["All", *sql.categories()])
    with right:
        sort = st.selectbox("Sort by", ["Newest", "Price: low to high", "Price: high to low", "Name"])
    products = sql.catalogue(search, category, sort)
    if not products:
        st.info("No products match those filters.")
    for start in range(0, len(products), 3):
        cards = st.columns(3)
        for card, product in zip(cards, products[start:start + 3]):
            with card.container(border=True, height="stretch"):
                image_path = sql.product_image_path(product["image_filename"])
                if image_path:
                    card_image = _product_card_image(
                        str(image_path), image_path.stat().st_mtime_ns
                    )
                    st.image(
                        card_image,
                        alt=f"{product['name']} product photo",
                        width="stretch",
                    )
                else:
                    st.image(
                        _product_card_placeholder(),
                        alt=f"No photo uploaded for {product['name']}",
                        width="stretch",
                    )
                st.badge(product["category_name"], color="blue")
                st.subheader(product["name"])
                st.caption(product["store_name"])
                st.markdown(f"**${product['price']:.2f}**")
                if product["stock_quantity"] <= 0:
                    st.badge("Out of stock", color="red")
                else:
                    st.caption(f"{product['stock_quantity']} in stock")
                rating = mongo.average_rating(product["product_id"])
                if rating:
                    st.caption(f"Customer rating: {rating:.1f} / 5")
                if st.button("View details", key=f"view-{product['product_id']}"):
                    mongo.record_view(user["user_id"] if user else 0, product["product_id"])
                    open_product(product["product_id"])
                if user and product["stock_quantity"] > 0:
                    if product_color_options(product["name"]):
                        st.caption("Choose a color on the product details page.")
                    else:
                        qty = st.number_input(
                            "Quantity",
                            min_value=1,
                            max_value=product["stock_quantity"],
                            value=1,
                            key=f"qty-{product['product_id']}",
                        )
                        if st.button("Add to cart", key=f"cart-{product['product_id']}"):
                            try:
                                sql.set_cart_item(
                                    user["user_id"], product["product_id"], int(qty)
                                )
                                st.success("Cart updated.")
                            except ValueError as exc:
                                st.error(str(exc))
    if user:
        st.page_link(cart_page, label="View cart", icon=":material/shopping_cart:")


def _render_product_page(
    sql: SQLStore,
    mongo: DocumentBackend,
    user: dict | None,
    shop_page,
    cart_page,
) -> None:
    product_id_value = st.query_params.get(
        "product", st.session_state.get("selected_product_id", "")
    )
    try:
        product_id = int(product_id_value)
    except (TypeError, ValueError):
        st.info("Choose a product from the shop to view its details.")
        st.page_link(shop_page, label="Back to shop", icon=":material/arrow_back:")
        return
    if st.query_params.get("product") != str(product_id):
        st.query_params["product"] = str(product_id)
    _product_detail(sql, mongo, user, product_id, shop_page, cart_page)


def _product_detail(
    sql: SQLStore,
    mongo: DocumentBackend,
    user: dict | None,
    product_id: int,
    shop_page,
    cart_page,
) -> None:
    product = sql.product(product_id)
    if not product:
        st.warning("That product is unavailable.")
        st.page_link(shop_page, label="Back to shop", icon=":material/arrow_back:")
        return
    st.page_link(shop_page, label="Back to shop", icon=":material/arrow_back:")
    st.header(product["name"])
    st.caption(f"{product['category_name']} · Sold by {product['store_name']}")
    detail_image, detail_text = st.columns([1, 1])
    with detail_image:
        image_path = sql.product_image_path(product["image_filename"])
        if image_path:
            st.image(str(image_path), alt=f"{product['name']} product photo", width="stretch")
        else:
            st.caption("Product photo not added yet")
    with detail_text:
        st.subheader(f"${product['price']:.2f}")
        out_of_stock = product["stock_quantity"] <= 0
        if out_of_stock:
            st.badge("Out of stock", color="red")
        else:
            st.badge(f"{product['stock_quantity']} in stock", color="green")
        st.subheader("About this product")
        description = product.get("details") or product.get("description")
        if description and description.strip():
            st.markdown(description)
        else:
            st.info("No product description has been added yet.")
        colors = product_color_options(product["name"])
        selected_color = ""
        if colors:
            color_choice = st.selectbox(
                "Color",
                ["Choose a color", *colors],
                key=f"detail-color-{product_id}",
            )
            if color_choice in colors:
                selected_color = color_choice
        if not out_of_stock:
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=product["stock_quantity"],
                value=1,
                key=f"detail-qty-{product_id}",
            )
            if user:
                if st.button("Add to cart", key=f"detail-cart-{product_id}", type="primary"):
                    if colors and not selected_color:
                        st.warning("Choose a color before adding this product to your cart.")
                    else:
                        try:
                            sql.set_cart_item(
                                user["user_id"],
                                product_id,
                                int(quantity),
                                color=selected_color,
                            )
                            st.success("Cart updated.")
                            st.page_link(
                                cart_page,
                                label="Go to cart",
                                icon=":material/shopping_cart:",
                            )
                        except ValueError as exc:
                            st.error(str(exc))
            else:
                st.button(
                    "Add to cart",
                    key=f"detail-cart-{product_id}",
                    type="primary",
                    disabled=True,
                )
                st.caption("Sign in to add this product to your cart.")
    specifications = mongo.specifications_for(product_id)
    if specifications:
        with st.expander("Specifications"):
            st.json(specifications)
    reviews = mongo.reviews_for(product_id)
    st.subheader("Customer reviews")
    average_rating = mongo.average_rating(product_id)
    st.caption(f"Average rating: {average_rating:.1f} / 5" if average_rating else "No reviews yet")
    for review in reviews:
        reviewer = review.get("reviewer_name")
        author = f" — {reviewer}" if reviewer else ""
        st.write(f"⭐ {review['rating']}/5{author} — {review['comment']}")
        if review.get("is_demo"):
            st.caption("Sample review")
        if review.get("color"):
            st.caption(f"Purchased: {product['name']} — {review['color']}")
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


def _cart(sql: SQLStore, user: dict, shop_page, orders_page) -> None:
    st.header("Your cart")
    cart = sql.cart(user["user_id"])
    if not cart:
        st.info("Your cart is empty.")
        st.page_link(shop_page, label="Continue shopping", icon=":material/storefront:")
        return
    for item in cart:
        with st.container(border=True):
            name_col, subtotal_col = st.columns([3, 1])
            name_col.subheader(item["name"])
            color_options = product_color_options(item["name"])
            selected_color = item["color"]
            if color_options:
                choices = ["Choose a color", *color_options]
                if selected_color not in color_options:
                    selected_color = "Choose a color"
                color_choice = st.selectbox(
                    "Color",
                    choices,
                    index=choices.index(selected_color),
                    key=f"cart-color-{item['product_id']}-{item['color'] or 'unset'}",
                )
                if color_choice in color_options:
                    selected_color = color_choice
                else:
                    selected_color = ""
            name_col.caption(
                f"Color: {item['color']} · Quantity: {item['quantity']}"
                if item["color"]
                else f"Quantity: {item['quantity']}"
            )
            if item["stock_quantity"] <= 0:
                name_col.badge("Out of stock", color="red")
            elif item["quantity"] > item["stock_quantity"]:
                name_col.warning(
                    f"Only {item['stock_quantity']} in stock. Update the quantity to continue."
                )
            subtotal_col.metric("Subtotal", f"${item['subtotal']:.2f}")
            quantity = st.number_input(
                "Quantity (0 to remove)",
                min_value=0,
                value=item["quantity"],
                key=f"edit-{item['product_id']}-{item['color'] or 'unset'}",
            )
            if st.button(
                "Update cart",
                key=f"update-{item['product_id']}-{item['color'] or 'unset'}",
            ):
                if color_options and not selected_color and int(quantity) > 0:
                    st.error("Choose a color before updating this cart item.")
                else:
                    try:
                        sql.set_cart_item(
                            user["user_id"],
                            item["product_id"],
                            int(quantity),
                            color=selected_color,
                            previous_color=item["color"],
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
    st.subheader("Checkout")
    total = sum(item["subtotal"] for item in cart)
    st.metric("Order total", f"${total:.2f}")
    unavailable_items = [
        item for item in cart if item["quantity"] > item["stock_quantity"]
    ]
    if unavailable_items:
        st.warning("Some items are out of stock or have less stock than requested. Update your cart before ordering.")
    missing_color_items = [
        item
        for item in cart
        if product_color_options(item["name"])
        and item["color"] not in product_color_options(item["name"])
    ]
    if missing_color_items:
        st.warning("Choose a color for each Ceramic Mug and Chino Shorts in your cart.")
    st.caption("Payment is simulated in this academic prototype.")
    if not unavailable_items and not missing_color_items:
        st.caption("Review your items above, then place your order.")
    if st.button(
        "Place order",
        type="primary",
        disabled=bool(unavailable_items or missing_color_items),
    ):
        try:
            order_id = sql.checkout(user["user_id"])
            st.session_state["order_confirmation"] = f"Order #{order_id} placed successfully."
            st.switch_page(orders_page)
        except ValueError as exc:
            st.error(str(exc))


def _orders(sql: SQLStore, user: dict) -> None:
    st.header("Order history")
    confirmation = st.session_state.pop("order_confirmation", None)
    if confirmation:
        st.success(confirmation)
    frame = order_frame(sql, user["user_id"])
    if frame.empty:
        st.info("No orders yet.")
    else:
        st.dataframe(frame, width="stretch", hide_index=True)


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
    st.dataframe(products, width="stretch", hide_index=True)
    if products:
        selected = st.selectbox("Update stock", products, format_func=lambda p: p["name"])
        quantity = st.number_input("New stock", min_value=0, value=int(selected["stock_quantity"]))
        if st.button("Save stock"):
            try:
                sql.update_inventory(user["user_id"], selected["product_id"], int(quantity))
                st.success("Inventory updated.")
            except (PermissionError, ValueError) as exc:
                st.error(str(exc))
        st.subheader("Product photos")
        photo_product_id = st.selectbox(
            "Choose a product",
            [product["product_id"] for product in products],
            format_func=lambda product_id: next(
                product["name"] for product in products if product["product_id"] == product_id
            ),
            key="photo-product",
        )
        photo_product = next(
            product for product in products if product["product_id"] == photo_product_id
        )
        current_image = sql.product_image_path(photo_product["image_filename"])
        if current_image:
            st.image(
                str(current_image),
                alt=f"Current photo of {photo_product['name']}",
                width=240,
            )
        else:
            st.caption("No photo uploaded for this product yet.")
        uploaded_image = st.file_uploader(
            "Upload a product photo (PNG, JPG, or WebP; up to 10 MB)",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"product-photo-{photo_product_id}",
        )
        if st.button(
            "Save product photo",
            key=f"save-product-photo-{photo_product_id}",
            disabled=uploaded_image is None,
        ):
            image_bytes = uploaded_image.getvalue()
            if len(image_bytes) > 10 * 1024 * 1024:
                st.error("The image must be 10 MB or smaller.")
            else:
                try:
                    with Image.open(BytesIO(image_bytes)) as image:
                        image_format = image.format
                        image_too_large = image.width * image.height > 20_000_000
                        image.verify()
                except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
                    st.error("That file is not a valid supported image.")
                else:
                    extensions = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
                    extension = extensions.get(image_format or "")
                    if image_too_large:
                        st.error("The image dimensions are too large.")
                    elif extension is None:
                        st.error("Upload a PNG, JPG, or WebP image.")
                    else:
                        try:
                            sql.save_product_image(
                                user["user_id"], photo_product_id, image_bytes, extension
                            )
                        except (OSError, PermissionError, ValueError) as exc:
                            st.error(str(exc))
                        else:
                            st.success("Product photo saved.")
                            st.rerun()
    st.subheader("Orders containing your products")
    st.dataframe(orders, width="stretch", hide_index=True)


def _admin_dashboard(sql: SQLStore, mongo: DocumentBackend) -> None:
    st.header("Admin dashboard")
    summary = sales_summary(sql)
    one, two, three = st.columns(3)
    one.metric("Total revenue", f"${summary['revenue']:.2f}")
    two.metric("Total orders", summary["orders"])
    three.metric("Product views", mongo.history_count())
    frame = order_frame(sql)
    if not frame.empty:
        st.bar_chart(
            frame.set_index("created_at")["total_amount"],
            alt="Order totals over time",
        )
    st.subheader("Most viewed products")
    st.dataframe(mongo.top_viewed(), width="stretch", hide_index=True)
    report = sql.analytics()
    st.subheader("Sales by category")
    st.dataframe(report["categories"], width="stretch", hide_index=True)
    source_reviews = mongo.source_review_summary()
    if source_reviews:
        st.subheader("Olist source order reviews")
        st.caption("Public dataset scores are order-level, not ShopSphere product reviews.")
        score_col, count_col = st.columns(2)
        score_col.metric("Average source score", f"{source_reviews['average_score']:.2f} / 5")
        count_col.metric("Imported source reviews", source_reviews["count"])
        st.dataframe(source_reviews["distribution"], width="stretch", hide_index=True)
    st.subheader("Low-stock alerts")
    st.dataframe(report["low_stock"], width="stretch", hide_index=True)


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
