# ShopSphere

ShopSphere is a runnable INF2003 hybrid database marketplace prototype. The
default `demo` mode uses SQLite and an in-memory document store, so the complete
customer, seller and admin demonstration works without database services.

## Run on Windows

From `C:\Users\kumar\Documents\ShopSphere`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r shopsphere\requirements.txt
Copy-Item shopsphere\.env.example shopsphere\.env
python -m pytest shopsphere\tests
streamlit run shopsphere\app.py
```

Demo accounts are `admin@shopsphere.local` / `Admin123!`,
`seller@shopsphere.local` / `Seller123!`, and
`customer@shopsphere.local` / `Customer123!`.

## Database design and deployment

MariaDB DDL, indexes, views and seed data are in [db](db). MongoDB collection
indexes are in [db/mongodb.js](db/mongodb.js). The application intentionally
uses SQLite/in-memory services in demo mode; this makes the presentation
reproducible while retaining optional MariaDB and MongoDB adapters in `db/`.
The checkout is a single SQLite/MariaDB transaction. MongoDB events are
independent writes, so a failed document write is reported rather than being
misrepresented as an atomic cross-database transaction.

## Data and measurement tools

Run `python -m shopsphere.scripts.import_olist --raw data/raw/olist` after downloading the
Olist CSV files. Run `python -m shopsphere.scripts.benchmark --repeats 30` to create actual
timings in `data/benchmark_results.csv`; no measurements are fabricated.
Supporting material is in [docs](docs), including the ERD, report draft,
testing checklist, manual, presentation outline and video script.

Product images, payments and shipping are intentionally simulated for this
academic prototype. Olist lacks account credentials, carts, live inventory and
configurable specifications; those demo-only features are clearly labelled.
