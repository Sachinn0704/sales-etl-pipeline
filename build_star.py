"""Transform public.raw_sales into a small sales star schema."""
import os

import pandas as pd
from sqlalchemy import create_engine, URL, text


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
    engine = get_engine()
    try:
        with engine.connect() as conn:
            raw = pd.read_sql(text("""
                SELECT order_id, order_date, customer_id, customer_name,
                       product_id, product_name, category, quantity,
                       unit_price, region
                FROM public.raw_sales
            """), conn)

        if raw.empty:
            raise ValueError("raw_sales is empty. Run python ingest.py first.")

        raw["order_date"] = pd.to_datetime(raw["order_date"], errors="raise").dt.date
        raw["quantity"] = pd.to_numeric(raw["quantity"], errors="raise").astype(int)
        raw["unit_price"] = pd.to_numeric(raw["unit_price"], errors="raise").round(2)
        raw["sales_amount"] = (raw["quantity"] * raw["unit_price"]).round(2)

        # Build dimensions using natural IDs, keeping one row per entity.
        customers = (raw[["customer_id", "customer_name", "region"]]
                     .drop_duplicates(subset=["customer_id"])
                     .sort_values("customer_id")
                     .reset_index(drop=True))
        customers.insert(0, "customer_key", range(1, len(customers) + 1))

        products = (raw[["product_id", "product_name", "category"]]
                    .drop_duplicates(subset=["product_id"])
                    .sort_values("product_id")
                    .reset_index(drop=True))
        products.insert(0, "product_key", range(1, len(products) + 1))

        dates = pd.DataFrame({"order_date": sorted(raw["order_date"].unique())})
        dates["date_key"] = pd.to_datetime(dates["order_date"]).dt.strftime("%Y%m%d").astype(int)
        dates["year"] = pd.to_datetime(dates["order_date"]).dt.year
        dates["quarter"] = pd.to_datetime(dates["order_date"]).dt.quarter
        dates["month"] = pd.to_datetime(dates["order_date"]).dt.month
        dates["month_name"] = pd.to_datetime(dates["order_date"]).dt.strftime("%B")
        dates["day"] = pd.to_datetime(dates["order_date"]).dt.day
        dates = dates[["date_key", "order_date", "year", "quarter", "month", "month_name", "day"]]

        facts = raw.merge(customers[["customer_id", "customer_key"]], on="customer_id", how="left")
        facts = facts.merge(products[["product_id", "product_key"]], on="product_id", how="left")
        facts = facts.merge(dates[["order_date", "date_key"]], on="order_date", how="left")
        facts = facts[[
            "order_id", "date_key", "customer_key", "product_key", "region",
            "quantity", "unit_price", "sales_amount"
        ]].copy()
        facts["quantity"] = facts["quantity"].astype(int)
        facts["unit_price"] = facts["unit_price"].astype(float)
        facts["sales_amount"] = facts["sales_amount"].astype(float)

        # Replace tables on each run, so rerunning the pipeline is repeatable.
        # Create dimensions before the fact table.
        customers.to_sql("dim_customer", engine, schema="public", if_exists="replace", index=False)
        products.to_sql("dim_product", engine, schema="public", if_exists="replace", index=False)
        dates.to_sql("dim_date", engine, schema="public", if_exists="replace", index=False)
        facts.to_sql("fact_sales", engine, schema="public", if_exists="replace", index=False)

        with engine.begin() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_fact_sales_date_key
                ON public.fact_sales (date_key)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_fact_sales_customer_key
                ON public.fact_sales (customer_key)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_fact_sales_product_key
                ON public.fact_sales (product_key)
            """))

        print(
            "Built star schema: "
            f"{len(customers)} customers, {len(products)} products, "
            f"{len(dates)} dates, {len(facts)} fact rows."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
