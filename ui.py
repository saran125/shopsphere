from __future__ import annotations

from html import escape

import streamlit as st

from .analytics import order_frame, sales_summary
from .document_store import DocumentStore, create_document_store
from .sql_store import SQLStore


# =========================================================
# DATABASE STORES
# =========================================================

@st.cache_resource
def stores() -> tuple[SQLStore, DocumentStore]:
    return SQLStore(), create_document_store()


# =========================================================
# THEME
# =========================================================

def _apply_theme(dark_mode: bool) -> None:
    if dark_mode:
        theme_css = """
<style>
:root {
    --primary: #7c6cff;
    --primary-dark: #6555ee;

    --text: #f8fafc;
    --muted: #a1a8b5;

    --background: #0f1117;
    --surface: #181b23;
    --surface-secondary: #20242e;

    --border: #2c313c;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(
            circle at top right,
            rgba(124,108,255,0.14),
            transparent 30%
        ),
        var(--background);

    color: var(--text);
}

[data-testid="stHeader"] {
    background: rgba(15,17,23,0.88);
    backdrop-filter: blur(12px);
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #0b0d13,
            #151823
        );
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #f8fafc !important;
}

.page-title {
    color: var(--text) !important;
}

.page-subtitle {
    color: var(--muted) !important;
}

.product-title {
    color: var(--text) !important;
}

.product-meta {
    color: var(--muted) !important;
}

.product-image {
    background:
        linear-gradient(
            135deg,
            #232637,
            #29243b
        ) !important;
}

.info-card {
    background: var(--surface) !important;
    border-color: var(--border) !important;
}

.card-title {
    color: var(--text) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface) !important;
    border-color: var(--border) !important;
}

[data-testid="stMetric"] {
    background: var(--surface) !important;
    border-color: var(--border) !important;
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
}

[data-testid="stMetricValue"] {
    color: var(--text) !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background: var(--surface-secondary) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

[data-baseweb="select"] > div {
    background: var(--surface-secondary) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

[data-baseweb="select"] span {
    color: var(--text) !important;
}

.stButton > button {
    background: var(--surface-secondary);
    color: var(--text);
    border-color: var(--border);
}

.stButton > button:hover {
    border-color: #7c6cff;
    color: #a99cff;
}

[data-testid="stDataFrame"] {
    background: var(--surface);
}
</style>
"""

    else:
        theme_css = """
<style>
:root {
    --primary: #6d5dfc;
    --primary-dark: #5548e8;

    --text: #111827;
    --muted: #6b7280;

    --background: #f7f8fc;
    --surface: #ffffff;
    --surface-secondary: #f0f1f7;

    --border: #e7e9f2;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(
            circle at top right,
            rgba(109,93,252,0.08),
            transparent 30%
        ),
        var(--background);

    color: var(--text);
}

[data-testid="stHeader"] {
    background: rgba(247,248,252,0.88);
    backdrop-filter: blur(12px);
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #151526,
            #23233d
        );
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #f8fafc !important;
}

.page-title {
    color: var(--text);
}

.page-subtitle {
    color: var(--muted);
}

.product-title {
    color: var(--text);
}

.product-meta {
    color: var(--muted);
}

.product-image {
    background:
        linear-gradient(
            135deg,
            #f0f0ff,
            #faf5ff
        );
}

.info-card {
    background: var(--surface);
    border-color: var(--border);
}

.card-title {
    color: var(--text);
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface);
    border-color: var(--border) !important;
}

[data-testid="stMetric"] {
    background: var(--surface);
    border-color: var(--border);
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-baseweb="select"] > div {
    background: white !important;
    color: #111827 !important;
}
</style>
"""

    common_css = """
<style>

.block-container {
    max-width: 1380px;
    padding-top: 1.6rem;
    padding-bottom: 4rem;
}

/* =========================================================
   HERO
========================================================= */

.hero {
    position: relative;
    overflow: hidden;

    padding: 3.2rem 3.4rem;
    margin-bottom: 2rem;

    border-radius: 28px;

    background:
        radial-gradient(
            circle at 88% 20%,
            rgba(255,255,255,0.25),
            transparent 20%
        ),
        radial-gradient(
            circle at 100% 100%,
            rgba(147,51,234,0.30),
            transparent 32%
        ),
        linear-gradient(
            120deg,
            #4338ca,
            #6366f1 50%,
            #7c3aed
        );

    box-shadow:
        0 25px 55px
        rgba(79,70,229,0.20);
}

.hero-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;

    padding: 0.35rem 0.8rem;

    border-radius: 999px;

    background: rgba(255,255,255,0.15);

    border:
        1px solid
        rgba(255,255,255,0.22);

    color: white !important;

    font-size: 0.77rem;
    font-weight: 700;

    letter-spacing: 0.06em;
}

.hero-title {
    margin-top: 1rem;
    margin-bottom: 0;

    color: white !important;

    font-size:
        clamp(2.5rem, 5vw, 4rem);

    line-height: 1.03;
    font-weight: 800;

    letter-spacing: -0.05em;
}

.hero-copy {
    max-width: 650px;

    margin-top: 1rem;

    color: #e8e7ff !important;

    font-size: 1.05rem;
    line-height: 1.7;
}


/* =========================================================
   PAGE TITLE
========================================================= */

.page-title {
    margin-bottom: 0.1rem;

    font-size: 1.9rem;
    font-weight: 800;

    letter-spacing: -0.035em;
}

.page-subtitle {
    margin-bottom: 1.5rem;

    font-size: 0.95rem;
}


/* =========================================================
   PRODUCT CARDS
========================================================= */

[data-testid="stVerticalBlockBorderWrapper"] {
    border:
        1px solid var(--border)
        !important;

    border-radius:
        20px !important;

    box-shadow:
        0 7px 24px
        rgba(15,23,42,0.05);

    transition:
        transform 180ms ease,
        box-shadow 180ms ease;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-4px);

    box-shadow:
        0 18px 35px
        rgba(15,23,42,0.10);
}

.product-image {
    height: 145px;

    display: flex;
    justify-content: center;
    align-items: center;

    margin-bottom: 1rem;

    border-radius: 16px;

    font-size: 4.2rem;
}

.category-pill {
    display: inline-block;

    margin-bottom: 0.6rem;

    padding:
        0.25rem
        0.65rem;

    border-radius: 999px;

    background: #eef2ff;

    color: #4f46e5;

    font-size: 0.73rem;
    font-weight: 700;
}

.product-title {
    margin-bottom: 0.3rem;

    font-size: 1.1rem;
    font-weight: 800;
}

.product-price {
    margin-top: 0.9rem;

    font-size: 1.6rem;
    font-weight: 800;

    color: #7c6cff;

    letter-spacing: -0.03em;
}

.product-meta {
    margin-top: 0.2rem;

    font-size: 0.82rem;
}


/* =========================================================
   BUTTONS
========================================================= */

.stButton > button {
    min-height: 2.6rem;

    border-radius: 11px;

    border:
        1px solid var(--border);

    font-weight: 700;

    transition: 0.15s ease;
}

.stButton > button:not([kind="primary"]) {
    background: var(--surface-secondary) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

.stButton > button:not([kind="primary"]):hover {
    background: var(--surface) !important;
    color: var(--primary) !important;
    border-color: var(--primary) !important;
}

.stButton > button[kind="primary"] {
    border: none;

    background:
        linear-gradient(
            90deg,
            #5b5cf0,
            #7c3aed
        );

    color: white;

    box-shadow:
        0 7px 18px
        rgba(91,92,240,0.22);
}


/* =========================================================
   INPUTS
========================================================= */

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-baseweb="select"] > div {
    border-radius: 11px;
}

[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
    color: var(--text) !important;
    opacity: 1 !important;
}


/* =========================================================
   METRICS
========================================================= */

[data-testid="stMetric"] {
    padding: 1.2rem;

    border:
        1px solid var(--border);

    border-radius: 18px;

    box-shadow:
        0 6px 20px
        rgba(15,23,42,0.04);
}


/* =========================================================
   CUSTOM CARDS
========================================================= */

.info-card {
    padding: 1.2rem;

    margin-bottom: 0.9rem;

    border:
        1px solid var(--border);

    border-radius: 16px;

    box-shadow:
        0 5px 18px
        rgba(15,23,42,0.04);
}

.small-label {
    color: #7c6cff;

    font-size: 0.75rem;
    font-weight: 800;

    letter-spacing: 0.05em;
}

.card-title {
    margin-top: 0.25rem;

    font-size: 1.05rem;
    font-weight: 800;
}

.status-pill {
    display: inline-block;

    margin-top: 0.5rem;

    padding:
        0.25rem
        0.6rem;

    border-radius: 999px;

    background: #ecfdf5;

    color: #047857;

    font-size: 0.75rem;
    font-weight: 700;
}


/* =========================================================
   MOBILE
========================================================= */

@media (max-width: 700px) {

    .hero {
        padding: 2rem;
        border-radius: 20px;
    }

    .block-container {
        padding-top: 1rem;
    }
}

</style>
"""

    st.markdown(
        theme_css + common_css,
        unsafe_allow_html=True
    )


# =========================================================
# HELPERS
# =========================================================

def _hero() -> None:
    html = (
        '<section class="hero">'
        '<div class="hero-chip">✨ ShopSphere Marketplace</div>'
        '<h1 class="hero-title">'
        'Find something<br>'
        'worth discovering.'
        '</h1>'
        '<p class="hero-copy">'
        'Explore products from independent sellers, '
        'discover new favourites and shop everything '
        'from one simple marketplace.'
        '</p>'
        '</section>'
    )

    st.markdown(
        html,
        unsafe_allow_html=True
    )


def _page_header(
    title: str,
    subtitle: str
) -> None:

    html = (
        f'<div class="page-title">{escape(title)}</div>'
        f'<div class="page-subtitle">{escape(subtitle)}</div>'
    )

    st.markdown(
        html,
        unsafe_allow_html=True
    )


def _product_icon(
    category: str
) -> str:

    category = category.lower()

    if "electronic" in category:
        return "💻"

    if "fashion" in category:
        return "👕"

    if "home" in category:
        return "🏠"

    if "book" in category:
        return "📚"

    if "sport" in category:
        return "⚽"

    if "beauty" in category:
        return "✨"

    if "food" in category:
        return "🍜"

    return "🛍️"


# =========================================================
# MAIN APP
# =========================================================

def run_app() -> None:

    st.set_page_config(
        page_title="ShopSphere",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ----------------------------
    # DARK MODE STATE
    # ----------------------------

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    if "user" not in st.session_state:
        st.session_state.user = None

    # ----------------------------
    # SIDEBAR TOP
    # ----------------------------

    with st.sidebar:

        st.markdown(
            "# 🛍️ ShopSphere"
        )

        st.caption(
            "INF2003 Database Systems"
        )

        new_dark_mode = st.toggle(
            "🌙 Dark mode",
            value=st.session_state.dark_mode
        )

        if (
            new_dark_mode
            != st.session_state.dark_mode
        ):
            st.session_state.dark_mode = (
                new_dark_mode
            )
            st.rerun()

        st.divider()

    # Apply theme after reading toggle state

    _apply_theme(
        st.session_state.dark_mode
    )

    sql, mongo = stores()

    _hero()

    # ----------------------------
    # ACCOUNT SIDEBAR
    # ----------------------------

    with st.sidebar:

        if st.session_state.user:

            user = st.session_state.user

            st.markdown(
                "### 👤 Account"
            )

            st.success(
                f"Signed in as\n\n"
                f"**{user['full_name']}**"
            )

            st.caption(
                f"Role: "
                f"{user['role'].title()}"
            )

            if st.button(
                "Log out",
                use_container_width=True
            ):

                st.session_state.user = None

                st.rerun()

        else:

            login_tab, register_tab = st.tabs(
                [
                    "Login",
                    "Register"
                ]
            )

            with login_tab:

                email = st.text_input(
                    "Email",
                    key="login_email"
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    key="login_password"
                )

                if st.button(
                    "Sign in",
                    type="primary",
                    use_container_width=True
                ):

                    user = sql.authenticate(
                        email,
                        password
                    )

                    if user:

                        st.session_state.user = (
                            user
                        )

                        st.rerun()

                    else:

                        st.error(
                            "Invalid email or password."
                        )

            with register_tab:

                name = st.text_input(
                    "Full name"
                )

                new_email = st.text_input(
                    "Email address"
                )

                new_password = st.text_input(
                    "Password",
                    type="password"
                )

                if st.button(
                    "Create account",
                    use_container_width=True
                ):

                    try:

                        sql.register(
                            new_email,
                            name,
                            new_password
                        )

                        st.success(
                            "Account created successfully."
                        )

                    except Exception as exc:

                        st.error(
                            str(exc)
                        )

    # =====================================================
    # PUBLIC VIEW
    # =====================================================

    user = st.session_state.user

    if not user:

        st.info(
            "👋 Browse the marketplace below. "
            "Log in to add products to your cart "
            "and place orders."
        )

        _catalogue(
            sql,
            mongo,
            None
        )

        return

    # =====================================================
    # NAVIGATION
    # =====================================================

    pages = [
        "🛍️ Catalogue",
        "🛒 Cart",
        "📦 My Orders",
        "👤 Profile"
    ]

    if user["role"] in {
        "seller",
        "admin"
    }:

        pages.append(
            "🏪 Seller Dashboard"
        )

    if user["role"] == "admin":

        pages.append(
            "📊 Admin Dashboard"
        )

    with st.sidebar:

        st.divider()

        page = st.radio(
            "Navigation",
            pages,
            label_visibility="collapsed"
        )

    if page == "🛍️ Catalogue":

        _catalogue(
            sql,
            mongo,
            user
        )

    elif page == "🛒 Cart":

        _cart(
            sql,
            user
        )

    elif page == "📦 My Orders":

        _orders(
            sql,
            user
        )

    elif page == "👤 Profile":

        _profile(
            sql,
            user
        )

    elif page == "🏪 Seller Dashboard":

        _seller_dashboard(
            sql,
            user
        )

    else:

        _admin_dashboard(
            sql,
            mongo
        )


# =========================================================
# CATALOGUE
# =========================================================

def _catalogue(
    sql: SQLStore,
    mongo: DocumentStore,
    user: dict | None
) -> None:

    _page_header(
        "Explore the marketplace",
        "Browse products from sellers across ShopSphere."
    )

    search_col, category_col, sort_col = (
        st.columns(
            [2.2, 1, 1]
        )
    )

    with search_col:

        search = st.text_input(
            "Search",
            placeholder=
            "Search products..."
        )

    with category_col:

        category = st.selectbox(
            "Category",
            [
                "All",
                *sql.categories()
            ]
        )

    with sort_col:

        sort = st.selectbox(
            "Sort by",
            [
                "Newest",
                "Price: low to high",
                "Price: high to low",
                "Name"
            ]
        )

    products = sql.catalogue(
        search,
        category,
        sort
    )

    st.caption(
        f"{len(products)} "
        f"product"
        f"{'s' if len(products) != 1 else ''} "
        f"found"
    )

    if not products:

        st.info(
            "No products match your filters."
        )

        return

    for start in range(
        0,
        len(products),
        3
    ):

        cols = st.columns(
            3,
            gap="large"
        )

        for col, product in zip(
            cols,
            products[
                start:start + 3
            ]
        ):

            with col:

                with st.container(
                    border=True
                ):

                    icon = _product_icon(
                        product[
                            "category_name"
                        ]
                    )

                    product_html = (
                        f'<div class="product-image">'
                        f'{icon}'
                        f'</div>'

                        f'<div class="category-pill">'
                        f'{escape(str(product["category_name"]))}'
                        f'</div>'

                        f'<div class="product-title">'
                        f'{escape(str(product["name"]))}'
                        f'</div>'
                    )

                    st.markdown(
                        product_html,
                        unsafe_allow_html=True
                    )

                    st.write(
                        product[
                            "description"
                        ]
                    )

                    price_html = (
                        f'<div class="product-price">'
                        f'${product["price"]:.2f}'
                        f'</div>'

                        f'<div class="product-meta">'
                        f'{escape(str(product["store_name"]))}'
                        f' · '
                        f'{product["stock_quantity"]}'
                        f' in stock'
                        f'</div>'
                    )

                    st.markdown(
                        price_html,
                        unsafe_allow_html=True
                    )

                    rating = (
                        mongo.average_rating(
                            product[
                                "product_id"
                            ]
                        )
                    )

                    if rating:

                        st.caption(
                            f"⭐ {rating}/5"
                        )

                    else:

                        st.caption(
                            "☆ No ratings yet"
                        )

                    if st.button(
                        "View details",
                        key=
                        f"view-{product['product_id']}",
                        use_container_width=True
                    ):

                        mongo.record_view(
                            user["user_id"]
                            if user
                            else 0,

                            product[
                                "product_id"
                            ]
                        )

                        st.session_state[
                            "selected_product"
                        ] = product[
                            "product_id"
                        ]

                    if user:

                        qty = st.number_input(
                            "Quantity",
                            min_value=1,

                            max_value=max(
                                1,
                                product[
                                    "stock_quantity"
                                ]
                            ),

                            value=1,

                            key=
                            f"qty-{product['product_id']}"
                        )

                        if st.button(
                            "🛒 Add to cart",

                            key=
                            f"cart-{product['product_id']}",

                            type="primary",

                            use_container_width=True
                        ):

                            try:

                                sql.set_cart_item(
                                    user[
                                        "user_id"
                                    ],

                                    product[
                                        "product_id"
                                    ],

                                    int(qty)
                                )

                                st.toast(
                                    "Added to cart!",
                                    icon="✅"
                                )

                            except ValueError as exc:

                                st.error(
                                    str(exc)
                                )

    selected = st.session_state.get(
        "selected_product"
    )

    if selected:

        st.divider()

        _product_detail(
            sql,
            mongo,
            user,
            selected
        )


# =========================================================
# PRODUCT DETAILS
# =========================================================

def _product_detail(
    sql: SQLStore,
    mongo: DocumentStore,
    user: dict | None,
    product_id: int
) -> None:

    product = sql.product(
        product_id
    )

    if not product:
        return

    _page_header(
        product["name"],
        "Product details and customer reviews."
    )

    left, right = st.columns(
        [1.2, 1]
    )

    with left:

        with st.container(
            border=True
        ):

            product_html = (
                f'<div class="product-image">'
                f'{_product_icon(product["category_name"])}'
                f'</div>'

                f'<div class="product-price">'
                f'${product["price"]:.2f}'
                f'</div>'
            )

            st.markdown(
                product_html,
                unsafe_allow_html=True
            )

            st.write(
                product[
                    "description"
                ]
            )

            st.caption(
                f"{product['stock_quantity']} "
                f"available"
            )

            st.markdown(
                "#### Specifications"
            )

            specs = (
                mongo.specifications.get(
                    product_id,

                    {
                        "attributes": {
                            "Information":
                            "No additional specifications"
                        }
                    }
                )
            )

            for key, value in (
                specs.get(
                    "attributes",
                    {}
                ).items()
            ):

                st.write(
                    f"**"
                    f"{key.replace('_', ' ').title()}"
                    f":** "
                    f"{value}"
                )

    with right:

        st.markdown(
            "### ⭐ Reviews"
        )

        avg = mongo.average_rating(
            product_id
        )

        if avg:

            st.metric(
                "Average rating",
                f"{avg}/5"
            )

        reviews = mongo.reviews_for(
            product_id
        )

        if not reviews:

            st.info(
                "No reviews yet."
            )

        for review in reviews:

            with st.container(
                border=True
            ):

                st.write(
                    "⭐"
                    * int(
                        review[
                            "rating"
                        ]
                    )
                )

                st.write(
                    review[
                        "comment"
                    ]
                )

        if user:

            st.markdown(
                "### Write a review"
            )

            with st.form(
                f"review-{product_id}"
            ):

                rating = st.slider(
                    "Rating",
                    1,
                    5,
                    5
                )

                comment = st.text_area(
                    "Review",

                    placeholder=
                    "Share your experience..."
                )

                if st.form_submit_button(
                    "Submit review",
                    use_container_width=True
                ):

                    mongo.add_review(
                        user[
                            "user_id"
                        ],

                        product_id,

                        rating,

                        comment
                    )

                    st.success(
                        "Review saved."
                    )

        if user:

            own_review = (
                mongo.review_for_user(
                    user[
                        "user_id"
                    ],
                    product_id
                )
            )

            if own_review:

                if st.button(
                    "Delete my review",
                    key=
                    f"delete-review-{product_id}"
                ):

                    mongo.delete_review(
                        user[
                            "user_id"
                        ],
                        product_id
                    )

                    st.success(
                        "Review deleted."
                    )

                    st.rerun()


# =========================================================
# CART
# =========================================================

def _cart(
    sql: SQLStore,
    user: dict
) -> None:

    _page_header(
        "Your cart",
        "Review your items before checkout."
    )

    cart = sql.cart(
        user[
            "user_id"
        ]
    )

    if not cart:

        st.info(
            "🛒 Your cart is empty."
        )

        return

    for item in cart:

        with st.container(
            border=True
        ):

            left, middle, right = (
                st.columns(
                    [3, 1, 1]
                )
            )

            with left:

                st.markdown(
                    f"### {item['name']}"
                )

                st.caption(
                    f"Subtotal: "
                    f"${item['subtotal']:.2f}"
                )

            with middle:

                quantity = (
                    st.number_input(
                        "Quantity",
                        min_value=0,
                        value=item[
                            "quantity"
                        ],

                        key=
                        f"edit-{item['product_id']}"
                    )
                )

            with right:

                st.write("")
                st.write("")

                if st.button(
                    "Update",

                    key=
                    f"update-{item['product_id']}",

                    use_container_width=True
                ):

                    try:

                        sql.set_cart_item(
                            user[
                                "user_id"
                            ],

                            item[
                                "product_id"
                            ],

                            int(quantity)
                        )

                        st.rerun()

                    except ValueError as exc:

                        st.error(
                            str(exc)
                        )

    total = sum(
        item[
            "subtotal"
        ]
        for item in cart
    )

    st.divider()

    left, right = st.columns(
        [2, 1]
    )

    with right:

        st.metric(
            "Order total",
            f"${total:.2f}"
        )

        if st.button(
            "Place order",
            type="primary",
            use_container_width=True
        ):

            try:

                order_id = (
                    sql.checkout(
                        user[
                            "user_id"
                        ]
                    )
                )

                st.success(
                    f"🎉 Order "
                    f"#{order_id} "
                    f"placed successfully!"
                )

                st.rerun()

            except ValueError as exc:

                st.error(
                    str(exc)
                )


# =========================================================
# ORDERS
# =========================================================

def _orders(
    sql: SQLStore,
    user: dict
) -> None:

    _page_header(
        "Order history",
        "Track your previous purchases."
    )

    frame = order_frame(
        sql,
        user[
            "user_id"
        ]
    )

    if frame.empty:

        st.info(
            "You have not placed any orders yet."
        )

        return

    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# SELLER DASHBOARD
# =========================================================

def _seller_dashboard(
    sql: SQLStore,
    user: dict
) -> None:

    _page_header(
        "Seller dashboard",
        "Manage your products, stock and orders."
    )

    try:

        products = (
            sql.seller_products(
                user[
                    "user_id"
                ]
            )
        )

        orders = (
            sql.seller_orders(
                user[
                    "user_id"
                ]
            )
        )

    except PermissionError as exc:

        st.error(
            str(exc)
        )

        return

    m1, m2 = st.columns(
        2
    )

    m1.metric(
        "Products",
        len(products)
    )

    m2.metric(
        "Order lines",
        len(orders)
    )

    st.markdown(
        "### 📦 Inventory"
    )

    st.dataframe(
        products,
        use_container_width=True,
        hide_index=True
    )

    if products:

        with st.container(
            border=True
        ):

            st.markdown(
                "### Update stock"
            )

            selected = st.selectbox(
                "Product",

                products,

                format_func=
                lambda p:
                p["name"]
            )

            quantity = st.number_input(
                "New stock quantity",

                min_value=0,

                value=int(
                    selected[
                        "stock_quantity"
                    ]
                )
            )

            if st.button(
                "Save inventory",
                type="primary"
            ):

                try:

                    sql.update_inventory(
                        user[
                            "user_id"
                        ],

                        selected[
                            "product_id"
                        ],

                        int(quantity)
                    )

                    st.success(
                        "Inventory updated."
                    )

                    st.rerun()

                except (
                    PermissionError,
                    ValueError
                ) as exc:

                    st.error(
                        str(exc)
                    )

    st.markdown(
        "### 🧾 Orders containing your products"
    )

    st.dataframe(
        orders,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def _admin_dashboard(
    sql: SQLStore,
    mongo: DocumentStore
) -> None:

    _page_header(
        "Admin dashboard",
        "Marketplace performance and operational overview."
    )

    summary = sales_summary(
        sql
    )

    one, two, three = st.columns(
        3
    )

    one.metric(
        "💰 Revenue",
        f"${summary['revenue']:.2f}"
    )

    two.metric(
        "📦 Orders",
        summary[
            "orders"
        ]
    )

    three.metric(
        "👀 Product views",
        len(
            mongo.history
        )
    )

    st.markdown(
        "### 📈 Sales overview"
    )

    orders = order_frame(
        sql
    )

    if not orders.empty:

        st.bar_chart(
            orders,
            x="created_at",
            y="total_amount"
        )

    report = sql.analytics()

    left, right = st.columns(
        2
    )

    with left:

        st.markdown(
            "### 🔥 Most viewed products"
        )

        viewed = mongo.top_viewed()

        if viewed:

            st.dataframe(
                viewed,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No product views yet."
            )

        st.markdown(
            "### 📊 Sales by category"
        )

        st.dataframe(
            report[
                "categories"
            ],
            use_container_width=True,
            hide_index=True
        )

    with right:

        st.markdown(
            "### ⚠️ Low stock alerts"
        )

        st.dataframe(
            report[
                "low_stock"
            ],
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# PROFILE
# =========================================================

def _profile(
    sql: SQLStore,
    user: dict
) -> None:

    _page_header(
        "Profile",
        "Manage your account information."
    )

    left, right = st.columns(
        [1.5, 1]
    )

    with left:

        with st.container(
            border=True
        ):

            name = st.text_input(
                "Full name",

                value=
                user[
                    "full_name"
                ]
            )

            email = st.text_input(
                "Email",

                value=
                user[
                    "email"
                ]
            )

            st.caption(
                f"Role: "
                f"{user['role'].title()}"
            )

            if st.button(
                "Save changes",
                type="primary"
            ):

                try:

                    sql.update_profile(
                        user[
                            "user_id"
                        ],

                        name,

                        email
                    )

                    st.session_state.user = {
                        **user,

                        "full_name":
                        name.strip(),

                        "email":
                        email.strip().lower()
                    }

                    st.success(
                        "Profile updated."
                    )

                except ValueError as exc:

                    st.error(
                        str(exc)
                    )

    with right:

        profile_html = (
            '<div class="info-card">'

            '<div class="small-label">'
            'ACCOUNT'
            '</div>'

            f'<div class="card-title">'
            f'{escape(str(user["full_name"]))}'
            f'</div>'

            f'<div class="product-meta">'
            f'{escape(str(user["email"]))}'
            f'</div>'

            f'<div class="status-pill">'
            f'{escape(str(user["role"]).title())}'
            f'</div>'

            '</div>'
        )

        st.markdown(
            profile_html,
            unsafe_allow_html=True
        )