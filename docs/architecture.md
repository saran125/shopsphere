# Architecture

Streamlit calls the application services in `sql_store.py` and the document
backend contract in `document_store.py`. SQLite is authoritative for users,
sellers, catalogue, inventory, carts, orders, and payments in both app modes.
Demo mode stores reviews, browsing history, and flexible specifications in
memory; MongoDB mode persists them in MongoDB.

MongoDB mode also stores Olist order-level reviews separately from ShopSphere
product reviews. The Olist importer puts relational product/catalogue data in
SQLite and flexible source attributes in MongoDB. Olist-derived inventory is
initialized to zero because the public source does not include live stock.

The MariaDB adapter and schema are retained for deployment/database coursework.
A checkout is transactional only inside SQLite. A browsing event or review is
a separate MongoDB write, so the system reports that failure instead of
claiming distributed atomicity.
