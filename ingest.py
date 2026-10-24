"""Extract local sales CSV and load it into PostgreSQL as raw_sales."""
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, URL, text

ROOT = Path(__file__).resolve().parent
CSV_PATH = Path(os.getenv("SALES_CSV_PATH", ROOT / "data" / "sales.csv"))

REQUIRED_COLUMNS = [
    "order_id", "order_date", "customer_id", "customer_name",
    "product_id", "product_name", "category", "quantity",
    "unit_price", "region",
]


def get_engine():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER", "etl_user"),
        password=os.getenv("DB_PASSWORD", "etl_password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "etl_db"),
    )
    return create_engine(url, pool_pre_ping=True)


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Sales CSV not found: {CSV_PATH}\n"
            "Put your CSV at data/sales.csv or set SALES_CSV_PATH."
        )

    df = pd.read_csv(CSV_PATH)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Expected columns: {REQUIRED_COLUMNS}"
        )

    df = df[REQUIRED_COLUMNS].copy()
    df["order_id"] = df["order_id"].astype("string").str.strip()
    df["customer_id"] = df["customer_id"].astype("string").str.strip()
    df["product_id"] = df["product_id"].astype("string").str.strip()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce").dt.date
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    if df.empty:
        raise ValueError("The CSV contains no data rows.")
    if df["order_id"].isna().any() or (df["order_id"].str.len() == 0).any():
        raise ValueError("order_id cannot be blank.")
    if df["order_date"].isna().any():
        raise ValueError("Some order_date values are invalid. Use YYYY-MM-DD.")
    if df["quantity"].isna().any() or (df["quantity"] <= 0).any():
        raise ValueError("quantity must be a positive number.")
    if df["unit_price"].isna().any() or (df["unit_price"] < 0).any():
        raise ValueError("unit_price must be a non-negative number.")

    for col in ["customer_name", "product_name", "category", "region"]:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()
        df.loc[df[col] == "", col] = "Unknown"

    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
        df.to_sql("raw_sales", engine, schema="public", if_exists="replace",
                  index=False, chunksize=1000, method="multi")
    finally:
        engine.dispose()

    print(f"Loaded {len(df):,} rows from {CSV_PATH} into public.raw_sales")


if __name__ == "__main__":
    main()
