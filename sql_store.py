from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from .config import settings


SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 user_id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL, full_name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('customer','seller','admin')) DEFAULT 'customer',
 is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sellers (
 seller_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL,
 store_name TEXT NOT NULL, description TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id));
CREATE TABLE IF NOT EXISTS categories (
 category_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, is_active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS products (
 product_id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
 name TEXT NOT NULL, description TEXT NOT NULL, price NUMERIC NOT NULL CHECK(price >= 0),
 is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(seller_id) REFERENCES sellers(seller_id), FOREIGN KEY(category_id) REFERENCES categories(category_id));
CREATE TABLE IF NOT EXISTS inventory (
 product_id INTEGER PRIMARY KEY, quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
 reorder_level INTEGER NOT NULL DEFAULT 5 CHECK(reorder_level >= 0), updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(product_id) REFERENCES products(product_id));
CREATE TABLE IF NOT EXISTS cart_items (
 user_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0),
 updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, product_id),
 FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(product_id) REFERENCES products(product_id));
CREATE TABLE IF NOT EXISTS orders (
 order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'paid',
 total_amount NUMERIC NOT NULL CHECK(total_amount >= 0), created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(user_id));
CREATE TABLE IF NOT EXISTS order_items (
 order_item_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
 seller_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0), unit_price NUMERIC NOT NULL,
 FOREIGN KEY(order_id) REFERENCES orders(order_id), FOREIGN KEY(product_id) REFERENCES products(product_id),
 FOREIGN KEY(seller_id) REFERENCES sellers(seller_id));
CREATE TABLE IF NOT EXISTS payments (
 payment_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER UNIQUE NOT NULL, amount NUMERIC NOT NULL,
 method TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'simulated', paid_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(order_id) REFERENCES orders(order_id));
"""


class SQLStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.sqlite_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _initialise(self) -> None:
        with self.connection() as conn:
            conn.executescript(SQLITE_SCHEMA)
            if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
                self.seed_demo(conn)

    def seed_demo(self, conn: sqlite3.Connection | None = None) -> None:
        own = conn is None
        context = self.connection() if own else _existing(conn)
        with context as active:
            from .security import hash_password
            users = [
                ("admin@shopsphere.local", "Admin User", "admin", "Admin123!"),
                ("seller@shopsphere.local", "Demo Seller", "seller", "Seller123!"),
                ("customer@shopsphere.local", "Demo Customer", "customer", "Customer123!"),
            ]
            for email, name, role, password in users:
                active.execute(
                    "INSERT OR IGNORE INTO users(email,password_hash,full_name,role) VALUES(?,?,?,?)",
                    (email, hash_password(password), name, role),
                )
            active.execute("INSERT OR IGNORE INTO sellers(user_id,store_name,description) "
                           "SELECT user_id,'SIT Demo Store','Quality demo products' FROM users WHERE role='seller'")
            for name in ("Electronics", "Home & Living", "Fashion", "Books"):
                active.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (name,))
            seller = active.execute("SELECT seller_id FROM sellers LIMIT 1").fetchone()[0]
            category = active.execute("SELECT category_id FROM categories WHERE name='Electronics'").fetchone()[0]
            if active.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
                products = [
                    ("Wireless Headphones", "Noise-cancelling over-ear headphones.", 89.90, 25),
                    ("USB-C Hub", "Seven-port aluminium USB-C hub.", 39.90, 40),
                    ("Desk Lamp", "Adjustable LED lamp for study desks.", 29.90, 8),
                ]
                for name, description, price, quantity in products:
                    cur = active.execute(
                        "INSERT INTO products(seller_id,category_id,name,description,price) VALUES(?,?,?,?,?)",
                        (seller, category, name, description, price),
                    )
                    active.execute("INSERT INTO inventory(product_id,quantity,reorder_level) VALUES(?,?,5)",
                                   (cur.lastrowid, quantity))

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        from .security import verify_password
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=? AND is_active=1", (email.strip().lower(),)).fetchone()
        return dict(row) if row and verify_password(password, row["password_hash"]) else None

    def register(self, email: str, full_name: str, password: str) -> int:
        from .security import hash_password
        if "@" not in email or not full_name.strip():
            raise ValueError("Enter a valid email address and full name.")
        with self.connection() as conn:
            try:
                cur = conn.execute("INSERT INTO users(email,password_hash,full_name) VALUES(?,?,?)",
                                   (email.strip().lower(), hash_password(password), full_name.strip()))
            except sqlite3.IntegrityError as exc:
                raise ValueError("An account with that email already exists.") from exc
            return int(cur.lastrowid)

    def update_profile(self, user_id: int, full_name: str, email: str) -> None:
        if not full_name.strip() or "@" not in email:
            raise ValueError("Enter a valid email address and full name.")
        with self.connection() as conn:
            try:
                conn.execute("UPDATE users SET full_name=?, email=? WHERE user_id=?",
                             (full_name.strip(), email.strip().lower(), user_id))
            except sqlite3.IntegrityError as exc:
                raise ValueError("That email address is already in use.") from exc

    def seller_id_for_user(self, user_id: int) -> int | None:
        with self.connection() as conn:
            row = conn.execute("SELECT seller_id FROM sellers WHERE user_id=?", (user_id,)).fetchone()
        return int(row[0]) if row else None

    def catalogue(self, search: str = "", category: str = "All", sort: str = "Newest") -> list[dict[str, Any]]:
        order = {"Price: low to high": "p.price ASC", "Price: high to low": "p.price DESC",
                 "Name": "p.name ASC", "Newest": "p.created_at DESC"}[sort]
        query = """SELECT p.*, c.name category_name, s.store_name, i.quantity stock_quantity
                   FROM products p JOIN categories c ON c.category_id=p.category_id
                   JOIN sellers s ON s.seller_id=p.seller_id JOIN inventory i ON i.product_id=p.product_id
                   WHERE p.is_active=1 AND c.is_active=1
                     AND (p.name LIKE ? OR p.description LIKE ?)"""
        params: list[Any] = [f"%{search}%", f"%{search}%"]
        if category != "All":
            query += " AND c.name=?"
            params.append(category)
        query += f" ORDER BY {order}"
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def categories(self) -> list[str]:
        with self.connection() as conn:
            return [row[0] for row in conn.execute("SELECT name FROM categories WHERE is_active=1 ORDER BY name")]

    def product(self, product_id: int) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("""SELECT p.*, c.name category_name, s.store_name, i.quantity stock_quantity
                                  FROM products p JOIN categories c USING(category_id)
                                  JOIN sellers s USING(seller_id) JOIN inventory i USING(product_id)
                                  WHERE p.product_id=? AND p.is_active=1""", (product_id,)).fetchone()
        return dict(row) if row else None

    def cart(self, user_id: int) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return [dict(row) for row in conn.execute("""SELECT c.product_id,c.quantity,p.name,p.price,
                (c.quantity*p.price) subtotal FROM cart_items c JOIN products p USING(product_id)
                WHERE c.user_id=? ORDER BY c.updated_at DESC""", (user_id,))]

    def set_cart_item(self, user_id: int, product_id: int, quantity: int) -> None:
        if quantity < 1:
            with self.connection() as conn:
                conn.execute("DELETE FROM cart_items WHERE user_id=? AND product_id=?", (user_id, product_id))
            return
        with self.connection() as conn:
            stock = conn.execute("SELECT quantity FROM inventory WHERE product_id=?", (product_id,)).fetchone()
            if not stock or quantity > stock[0]:
                raise ValueError("Requested quantity exceeds available stock.")
            conn.execute("""INSERT INTO cart_items(user_id,product_id,quantity) VALUES(?,?,?)
                            ON CONFLICT(user_id,product_id) DO UPDATE SET quantity=excluded.quantity,
                            updated_at=CURRENT_TIMESTAMP""", (user_id, product_id, quantity))

    def create_product(self, user_id: int, category_id: int, name: str,
                       description: str, price: float, quantity: int) -> int:
        seller_id = self.seller_id_for_user(user_id)
        if seller_id is None:
            raise PermissionError("Only sellers can create products.")
        if not name.strip() or price < 0 or quantity < 0:
            raise ValueError("Product name, price and stock are invalid.")
        with self.connection() as conn:
            cur = conn.execute(
                "INSERT INTO products(seller_id,category_id,name,description,price) VALUES(?,?,?,?,?)",
                (seller_id, category_id, name.strip(), description.strip(), price))
            conn.execute("INSERT INTO inventory(product_id,quantity) VALUES(?,?)",
                         (cur.lastrowid, quantity))
            return int(cur.lastrowid)

    def update_product(self, user_id: int, product_id: int, **fields: Any) -> None:
        seller_id = self.seller_id_for_user(user_id)
        allowed = {"name", "description", "price", "category_id"}
        changes = {key: value for key, value in fields.items() if key in allowed}
        if seller_id is None or not changes:
            raise PermissionError("A seller account and at least one product field are required.")
        if "price" in changes and changes["price"] < 0:
            raise ValueError("Price cannot be negative.")
        with self.connection() as conn:
            owned = conn.execute("SELECT 1 FROM products WHERE product_id=? AND seller_id=?",
                                 (product_id, seller_id)).fetchone()
            if not owned:
                raise PermissionError("You can only modify your own products.")
            assignments = ", ".join(f"{key}=?" for key in changes)
            conn.execute(f"UPDATE products SET {assignments} WHERE product_id=?",
                         (*changes.values(), product_id))

    def update_inventory(self, user_id: int, product_id: int, quantity: int) -> None:
        if quantity < 0:
            raise ValueError("Stock cannot be negative.")
        seller_id = self.seller_id_for_user(user_id)
        with self.connection() as conn:
            changed = conn.execute(
                "UPDATE inventory SET quantity=?, updated_at=CURRENT_TIMESTAMP "
                "WHERE product_id=? AND EXISTS (SELECT 1 FROM products WHERE product_id=? AND seller_id=?)",
                (quantity, product_id, product_id, seller_id)).rowcount
        if changed != 1:
            raise PermissionError("You can only update inventory for your own products.")

    def seller_products(self, user_id: int) -> list[dict[str, Any]]:
        seller_id = self.seller_id_for_user(user_id)
        if seller_id is None:
            raise PermissionError("Seller access required.")
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                """SELECT p.*, c.name category_name, i.quantity stock_quantity
                   FROM products p JOIN categories c USING(category_id)
                   JOIN inventory i USING(product_id)
                   WHERE p.seller_id=? ORDER BY p.created_at DESC""", (seller_id,))]

    def checkout(self, user_id: int, method: str = "simulated_card") -> int:
        with self.connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute("""SELECT c.product_id,c.quantity,p.price,p.seller_id,i.quantity stock
                    FROM cart_items c JOIN products p USING(product_id) JOIN inventory i USING(product_id)
                    WHERE c.user_id=? AND p.is_active=1""", (user_id,)).fetchall()
                if not rows:
                    raise ValueError("Your cart is empty.")
                if any(row["quantity"] > row["stock"] for row in rows):
                    raise ValueError("Stock changed; reduce your cart quantity and try again.")
                total = sum(Decimal(str(row["price"])) * row["quantity"] for row in rows)
                cur = conn.execute("INSERT INTO orders(user_id,status,total_amount) VALUES(?,?,?)",
                                   (user_id, "paid", str(total)))
                order_id = int(cur.lastrowid)
                for row in rows:
                    updated = conn.execute("""UPDATE inventory SET quantity=quantity-?
                                              WHERE product_id=? AND quantity>=?""",
                                           (row["quantity"], row["product_id"], row["quantity"]))
                    if updated.rowcount != 1:
                        raise ValueError("Stock changed during checkout; no order was created.")
                    conn.execute("""INSERT INTO order_items(order_id,product_id,seller_id,quantity,unit_price)
                                    VALUES(?,?,?,?,?)""", (order_id, row["product_id"], row["seller_id"],
                                                            row["quantity"], row["price"]))
                conn.execute("INSERT INTO payments(order_id,amount,method) VALUES(?,?,?)",
                             (order_id, str(total), method))
                conn.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
                conn.execute("COMMIT")
                return order_id
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def orders(self, user_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT o.*, u.full_name FROM orders o JOIN users u USING(user_id)"
        params: tuple[Any, ...] = ()
        if user_id is not None:
            query += " WHERE o.user_id=?"
            params = (user_id,)
        query += " ORDER BY o.created_at DESC"
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(query, params)]

    def seller_orders(self, user_id: int) -> list[dict[str, Any]]:
        seller_id = self.seller_id_for_user(user_id)
        if seller_id is None:
            raise PermissionError("Seller access required.")
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(
                """SELECT o.order_id, o.created_at, o.status, u.full_name customer,
                          p.name product, oi.quantity, oi.unit_price,
                          oi.quantity * oi.unit_price revenue
                   FROM order_items oi JOIN orders o USING(order_id)
                   JOIN users u USING(user_id) JOIN products p USING(product_id)
                   WHERE oi.seller_id=? ORDER BY o.created_at DESC""", (seller_id,))]

    def analytics(self) -> dict[str, list[dict[str, Any]]]:
        with self.connection() as conn:
            revenue = [dict(row) for row in conn.execute(
                "SELECT date(created_at) day, SUM(total_amount) revenue, COUNT(*) orders "
                "FROM orders GROUP BY date(created_at) ORDER BY day")]
            categories = [dict(row) for row in conn.execute(
                """SELECT c.name category, SUM(oi.quantity * oi.unit_price) revenue,
                          SUM(oi.quantity) units
                   FROM order_items oi JOIN products p USING(product_id)
                   JOIN categories c USING(category_id)
                   GROUP BY c.category_id HAVING SUM(oi.quantity) > 0
                   ORDER BY revenue DESC""")]
            low_stock = [dict(row) for row in conn.execute(
                """SELECT p.product_id,p.name,i.quantity,i.reorder_level
                   FROM products p JOIN inventory i USING(product_id)
                   WHERE i.quantity <= i.reorder_level ORDER BY i.quantity""")]
        return {"revenue": revenue, "categories": categories, "low_stock": low_stock}


@contextmanager
def _existing(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    yield conn
