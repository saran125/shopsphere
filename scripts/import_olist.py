"""Import the supported subset of Olist CSV files into the demo SQLite store.

This script never invents source rows: missing files or columns are reported
and skipped. Passwords and marketplace-only features remain synthetic demo data.
"""
import argparse
import csv
from pathlib import Path

from shopsphere.sql_store import SQLStore


def read_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
        return list(reader)


def import_products(store: SQLStore, raw: Path) -> int:
    rows = read_rows(raw / "olist_products_dataset.csv",
                     {"product_id", "product_category_name"})
    if not rows:
        return 0
    category_ids: dict[str, int] = {}
    with store.connection() as conn:
        for row in rows:
            category = row["product_category_name"] or "Uncategorised"
            conn.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (category,))
            category_ids[category] = conn.execute(
                "SELECT category_id FROM categories WHERE name=?", (category,)).fetchone()[0]
        seller = conn.execute("SELECT seller_id FROM sellers LIMIT 1").fetchone()[0]
        imported = 0
        for row in rows:
            name = f"Olist product {row['product_id']}"
            cur = conn.execute(
                "INSERT OR IGNORE INTO products(seller_id,category_id,name,description,price) "
                "VALUES(?,?,?,?,?)",
                (seller, category_ids[row["product_category_name"] or "Uncategorised"],
                 name, "Imported from Olist; price is supplied by order-item records.", 0),
            )
            if cur.rowcount:
                conn.execute("INSERT OR IGNORE INTO inventory(product_id,quantity) VALUES(?,0)",
                             (cur.lastrowid,))
                imported += 1
    return imported


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw/olist"))
    parser.add_argument("--sqlite", type=Path, default=Path("data/shopsphere.db"))
    args = parser.parse_args()
    imported = import_products(SQLStore(args.sqlite), args.raw)
    print(f"Imported {imported} product rows. Missing source files are skipped.")


if __name__ == "__main__":
    main()
