# Architecture

Streamlit calls the application services in `sql_store.py` and
`document_store.py`. In demo mode, SQLite is authoritative for users, sellers,
catalogue, inventory, carts, orders and payments; the in-memory document store
contains reviews, browsing history and flexible specifications.

Deployment mode can use [db/mariadb_store.py](../db/mariadb_store.py) and
[db/mongodb_store.py](../db/mongodb_store.py). A checkout is transactional only
inside the relational database. A browsing event or review is a separate
MongoDB write, so the system reports that failure instead of claiming distributed
atomicity.
