"""Load the Kaggle Olist CSV files with COPY. Header-driven, so column order does not matter."""
from __future__ import annotations

import csv
from pathlib import Path

FILES = [  # parents first
    ("olist_customers_dataset.csv", "customers"),
    ("olist_sellers_dataset.csv", "sellers"),
    ("product_category_name_translation.csv", "product_category_translation"),
    ("olist_products_dataset.csv", "products"),
    ("olist_orders_dataset.csv", "orders"),
    ("olist_order_items_dataset.csv", "order_items"),
    ("olist_order_payments_dataset.csv", "order_payments"),
    ("olist_order_reviews_dataset.csv", "order_reviews"),
]


def load_csv_dir(conn, directory: str | Path) -> dict[str, int]:
    directory = Path(directory)
    counts: dict[str, int] = {}
    for filename, table in FILES:
        path = directory / filename
        if not path.exists():
            raise FileNotFoundError(f"missing {path}")
        # utf-8-sig: some Olist files start with a hidden BOM that would corrupt the first column name
        with open(path, newline="", encoding="utf-8-sig") as f:
            header = [h.strip() for h in next(csv.reader(f))]
        cols = ", ".join(header)
        with conn.cursor() as cur:
            with cur.copy(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
                with open(path, "rb") as f:
                    while chunk := f.read(1 << 20):
                        cp.write(chunk)
            cur.execute(f"SELECT count(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    return counts