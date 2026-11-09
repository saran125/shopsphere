# User manual

1. Create a virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Run `python -m shopsphere.scripts.verify`.
4. Start the interface with `streamlit run app.py`.

Use the demo accounts in the README. Customers can browse, review, add to cart
and checkout. Sellers can update their own inventory. Administrators can view
platform totals, category sales, low-stock alerts and browsing activity.

For MariaDB, install the optional `mariadb` driver, execute
`db/schema.sql`, `db/indexes.sql`, `db/views.sql` and
`db/seed.sql` in that order. For MongoDB, run `mongosh db/mongodb.js` and set
the connection variables in `.env`.
