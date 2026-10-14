"""Create tables, load data, add constraints, create the read-only role.

Usage:
  python -m scripts.init_db --sample
  python -m scripts.init_db --csv-dir data/olist
"""
from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from app.config import get_settings
from scripts.load_csv import load_csv_dir
from scripts.sample_data import load_sample

DB_DIR = Path(__file__).resolve().parent.parent / "db"


def init_db(dsn: str, sample: bool = False, csv_dir: str | None = None) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute((DB_DIR / "schema.sql").read_text())
        if sample:
            load_sample(conn)
        elif csv_dir:
            print(load_csv_dir(conn, csv_dir))
        conn.execute((DB_DIR / "constraints.sql").read_text())
        conn.execute((DB_DIR / "roles.sql").read_text())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true", help="synthetic sample data")
    g.add_argument("--csv-dir", help="folder with the Kaggle Olist CSV files")
    args = ap.parse_args()
    init_db(get_settings().admin_dsn, sample=args.sample, csv_dir=args.csv_dir)
    print("database ready")
