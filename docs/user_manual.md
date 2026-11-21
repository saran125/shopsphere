# ShopSphere user and setup manual

## 1. Install and start the demo

Open PowerShell in the project root (the folder containing `shopsphere`):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3 -m pip install -r shopsphere\requirements.txt
if (-not (Test-Path shopsphere\.env)) { Copy-Item shopsphere\.env.example shopsphere\.env }
py -3 -m streamlit run shopsphere\app.py
```

Demo mode is the default (`APP_MODE=demo`). It uses the SQLite file at
`data\shopsphere.db` and an in-memory document store. The database is
initialized with demo data the first time the app starts. Use:

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@shopsphere.local` | `Admin123!` |
| Seller | `seller@shopsphere.local` | `Seller123!` |
| Customer | `customer@shopsphere.local` | `Customer123!` |

## 2. Connect MongoDB

Start Docker Desktop, then start MongoDB from PowerShell:

```powershell
docker run --name shopsphere-mongo -p 127.0.0.1:27017:27017 -d mongo:8.0
```

For a previously created container, run `docker start shopsphere-mongo`.
In `shopsphere\.env`, set:

```dotenv
APP_MODE=mongodb
MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DATABASE=shopsphere
```

From the project root, copy and run the collection validator/index setup
script inside the container:

```powershell
docker cp shopsphere\db\mongodb.js shopsphere-mongo:/tmp/mongodb.js
docker exec shopsphere-mongo mongosh --quiet --file /tmp/mongodb.js
```

Start the app with the command in section 1. SQLite remains the source of truth
for users, products, stock, carts, and orders. MongoDB persists ShopSphere
reviews, browsing history, flexible product specifications, and the separate
Olist order-review collection. The app reports MongoDB connection errors and
does not silently fall back to memory. Checkout is transactional within
SQLite, not across the two databases.

## 3. Shop as a customer

1. Sign in with the customer demo account.
2. Browse the shop, filter by category, or search for a product.
3. Select **Details** to open the product page. Review its description, rating,
   stock, available color variants, and quantity selector.
4. Choose the desired color where offered, select a quantity, and add the item
   to the cart. Ceramic Mug and Chino Shorts offer Beige and Blue options.
5. Open **Cart / Checkout** to change quantities, remove items, review the
   total, and place the simulated order. The app rechecks stock during checkout.
6. Use **Orders** to review previous purchases. Submit product reviews from
   product details when signed in as a customer.

Products with no inventory are labeled **Out of stock** and cannot be added to
the cart. Both app modes seed 2–4 fictional sample reviews per active product,
visibly marked **Sample review**. Demo samples are in memory; MongoDB-mode
samples persist in MongoDB. They are not customer-submitted reviews or Olist
source reviews. Customer-submitted product reviews remain separate from Olist
order-level reviews.

## 4. Manage a store as a seller

Sign in using the seller demo account and open the Seller dashboard. Sellers
can update inventory, manage their own products, inspect order information,
and upload or replace product photos. Photos can be PNG, JPG, or WebP up to
10 MB. Image files are stored under `product_images` next to the SQLite
database, and the product row stores the filename. The storefront keeps
consistent image frames without stretching the image.

## 5. Review analytics as an administrator

Sign in using the administrator demo account and open the Admin dashboard.
It provides platform totals, category sales, low-stock alerts, and browsing
activity. When Olist order reviews have been imported, it also shows their
score distribution and average. Olist scores describe source orders, not
ShopSphere products, and are not combined with ShopSphere's product ratings.

## 6. Import Olist source data

Download the [Brazilian E-Commerce Public Dataset by Olist on
Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), sign in
to Kaggle yourself, and extract the archive to `data\raw\olist`. The importer
needs `olist_products_dataset.csv`, `olist_order_items_dataset.csv`, and
`olist_order_reviews_dataset.csv` in that folder. The optional
`product_category_name_translation.csv` provides readable English category
names.

The dataset is licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Credit
Olist and retain the license when presenting or redistributing derived data.
The source spans historical Brazilian marketplace orders; it does not provide
current inventory or exact retail product names. The importer therefore uses
generic category labels such as `Garden Tools Item 01`, not claims about the
exact item, along with observed categories and average item prices. Source IDs
are retained as metadata, and new products start with zero stock. Replace the
generic names and placeholder descriptions with your own before presenting
them as specific items. Re-imports preserve names and descriptions you have
edited. Product specifications and order reviews are marked as Olist-sourced.
Reviews remain separate because each score belongs to an order, not to an app
product.

With Docker MongoDB running and `APP_MODE=mongodb`, run from the project root:

```powershell
py -3 -m shopsphere.scripts.import_olist --data-dir data\raw\olist --sqlite data\shopsphere.db --limit-products 100 --limit-reviews 500
```

The defaults import up to 100 products with the most observed order items and
a deterministic sample of up to 500 order reviews. Re-running updates the same
source records. SQL product rows are written transactionally; a later MongoDB
specification-write failure is shown explicitly and the command can be rerun.

## 7. Run tests

From the project root:

```powershell
py -3 -m pytest shopsphere\tests
```

To include the MongoDB integration test, set a connection URI in the current
PowerShell session before running pytest:

```powershell
$env:MONGODB_TEST_URI = "mongodb://127.0.0.1:27017"
py -3 -m pytest shopsphere\tests
Remove-Item Env:\MONGODB_TEST_URI
```

The integration test creates a unique temporary database and drops it when the
test finishes.
