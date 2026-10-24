"""Run basic data quality checks against the loaded sales star schema."""
import os
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
    checks = [
        ("raw_sales has rows", "SELECT COUNT(*) FROM public.raw_sales", lambda n: n > 0),
        ("fact_sales has rows", "SELECT COUNT(*) FROM public.fact_sales", lambda n: n > 0),
        ("no null order IDs", "SELECT COUNT(*) FROM public.fact_sales WHERE order_id IS NULL OR BTRIM(order_id) = ''", lambda n: n == 0),
        ("no invalid quantities", "SELECT COUNT(*) FROM public.fact_sales WHERE quantity IS NULL OR quantity <= 0", lambda n: n == 0),
        ("no negative sales amounts", "SELECT COUNT(*) FROM public.fact_sales WHERE sales_amount IS NULL OR sales_amount < 0", lambda n: n == 0),
        ("all dimension keys resolved", """
            SELECT COUNT(*) FROM public.fact_sales f
            LEFT JOIN public.dim_customer c ON f.customer_key = c.customer_key
            LEFT JOIN public.dim_product p ON f.product_key = p.product_key
            LEFT JOIN public.dim_date d ON f.date_key = d.date_key
            WHERE c.customer_key IS NULL OR p.product_key IS NULL OR d.date_key IS NULL
        """, lambda n: n == 0),
    ]

    failed = []
    engine = get_engine()
    try:
        with engine.connect() as conn:
            for name, sql, predicate in checks:
                value = conn.execute(text(sql)).scalar_one()
                passed = predicate(value)
                print(f"[{'PASS' if passed else 'FAIL'}] {name} (check value: {value})")
                if not passed:
                    failed.append(name)
    finally:
        engine.dispose()

    if failed:
        raise SystemExit("Data quality checks failed: " + ", ".join(failed))
    print("All data quality checks passed.")


if __name__ == "__main__":
    main()
