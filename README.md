# ShopSphere

ShopSphere is an INF2003 marketplace prototype built with Streamlit, SQLite,
and MongoDB. Demo mode is the default and needs no database server. MongoDB
mode uses SQLite for accounts, products, stock, carts, and orders, and a real
MongoDB database for reviews, browsing history, flexible product
specifications, and separately identified source review data.

## Setup on Windows

Run these commands from the project root (the directory containing the
`shopsphere` folder):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install -r shopsphere\requirements.txt
if (-not (Test-Path shopsphere\.env)) { Copy-Item shopsphere\.env.example shopsphere\.env }
py -3 -m pytest shopsphere\tests
py -3 -m streamlit run shopsphere\app.py
```

Demo accounts:

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@shopsphere.local` | `Admin123!` |
| Seller | `seller@shopsphere.local` | `Seller123!` |
| Customer | `customer@shopsphere.local` | `Customer123!` |

## Run with MongoDB

1. Start Docker Desktop. In PowerShell, start a local MongoDB container bound
   only to this computer:

   ```powershell
   docker run --name shopsphere-mongo -p 127.0.0.1:27017:27017 -d mongo:8.0
   ```

   If the container already exists, use `docker start shopsphere-mongo`.
2. In `shopsphere\.env`, set `APP_MODE=mongodb`. Keep
   `MONGODB_URI=mongodb://127.0.0.1:27017` and
   `MONGODB_DATABASE=shopsphere` for this local setup.
3. From the project root, create the MongoDB collections, validators, and
   indexes:

   ```powershell
   docker cp shopsphere\db\mongodb.js shopsphere-mongo:/tmp/mongodb.js
   docker exec shopsphere-mongo mongosh --quiet --file /tmp/mongodb.js
   ```

4. Start the app using the setup command above. MongoDB connection errors are
   reported; MongoDB mode does not silently switch to the in-memory demo
   document store.

`APP_MODE=demo` uses SQLite and an in-memory document store. The app always
uses SQLite for relational marketplace data; MongoDB mode persists document
data in MongoDB. Checkout is transactional within SQLite only, not across
SQLite and MongoDB.

## Import source-backed Olist data

Download the [Brazilian E-Commerce Public Dataset by Olist on
Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Kaggle
requires an account and acceptance of its dataset terms; do not share account
credentials. The dataset is licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Cite
Olist and this license when presenting or redistributing derived data.

Extract the archive into `data\raw\olist` so these files are directly inside
that folder:

- `olist_products_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `product_category_name_translation.csv` (optional; translates categories)

With MongoDB running and `APP_MODE=mongodb`, run from the project root:

```powershell
py -3 -m shopsphere.scripts.import_olist --data-dir data\raw\olist --sqlite data\shopsphere.db --limit-products 100 --limit-reviews 500
```

The importer selects up to 100 products with the most observed order items,
uses their source category (translated when the optional translation file is
present) and average sold-item price, and stores the Olist product ID and
category/weight/dimension attributes. Olist does not provide
exact retail product names or current stock. Products therefore receive
honest, category-based labels such as `Garden Tools Item 01`; these identify a
broad category, not the exact item. Their Olist IDs remain stored as source
metadata. Replace the generic names and placeholder descriptions with your own
before presenting them as specific products. New imports and reruns preserve
names/descriptions you have edited. Products start with zero inventory (out of
stock) rather than invented availability. Product/category data is stored in
SQLite; flexible specifications and up to 500 deterministically
sampled order-level reviews are stored in MongoDB. Olist reviews describe
orders, not ShopSphere products, and are kept in a separate collection and
clearly identified in the admin summary. Re-running the importer updates the
same products and reviews rather than duplicating them.

The SQL product writes are transactional. SQL and MongoDB do not share a
distributed transaction; if saving specifications fails after the SQL import,
the command reports the error and can be safely rerun.

## Using the application

- **Customers:** browse and filter products, open product details, choose
  quantity and available color, add items to the combined Cart/Checkout page,
  place an order, view order history, and submit product reviews.
- **Sellers:** manage their own products and inventory, view orders, and upload
  or replace product photos from the Seller dashboard.
- **Administrators:** review platform totals, category sales, low-stock alerts,
  browsing activity, and the separately aggregated Olist order-review scores.

Product details display the description in the relational `products` table.
Zero-stock products are marked **Out of stock** and cannot be purchased.
Ceramic Mug and Chino Shorts offer Beige and Blue variants. Product photos are
stored in a `product_images` folder next to the SQLite database; images are
shown in uniform 4:3 frames without stretching.

Both document backends seed 2–4 fictional sample reviews per active product.
Each is visibly labeled **Sample review**; in MongoDB mode they persist in
MongoDB and are not Olist or customer-submitted reviews. Re-running app setup
updates these samples without duplicating them. Customer reviews and Olist's
separate source order reviews remain distinguishable.

## Tests and project references

Run the local tests with `py -3 -m pytest shopsphere\tests`. To run the
MongoDB integration test against a disposable local test database, set
`MONGODB_TEST_URI=mongodb://127.0.0.1:27017` in the same PowerShell session
before running pytest. The integration test creates and drops its own uniquely
named database.

Run `py -3 -m shopsphere.scripts.benchmark --repeats 30` to create
`data/benchmark_results.csv` with actual timings. See [docs](docs) for the
architecture, ERD, testing guide, user manual, and project materials.

Payments and shipping are simulated. Olist does not contain ShopSphere user
accounts, carts, live inventory, or the app's custom product specifications.
