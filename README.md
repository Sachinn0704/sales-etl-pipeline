# Sales ETL Pipeline (PostgreSQL + Metabase)

## Included
- `data/sales.csv`: small example dataset. Replace it with your own CSV if desired.
- `ingest.py`: validates and loads the CSV into `public.raw_sales`.
- `build_star.py`: creates `dim_customer`, `dim_product`, `dim_date`, and `fact_sales`.
- `checks.py`: checks row counts, null IDs, quantities, amounts, and dimension-key resolution.
- `run_pipeline.py`: runs the three stages in order.
- `requirements.txt`: Python dependencies.
- `.env.example`: reference for connection settings. Scripts use these defaults unless environment variables override them.

## Prerequisites
Docker Compose services are already running, with PostgreSQL mapped to Windows port 5432.
The scripts run on Windows, so DB_HOST should be `localhost`, not `postgres`. `postgres` is only the hostname from another container on the same Compose network.

## Run in PowerShell
```powershell
cd C:\Users\Hp\etl_pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_pipeline.py
```

If PowerShell blocks venv activation, use this for the current terminal only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Tables created
- `raw_sales`
- `dim_customer`
- `dim_product`
- `dim_date`
- `fact_sales`

**Warning:** `ingest.py` replaces `raw_sales` on each run, and `build_star.py` replaces the four dimension/fact tables on each run. This makes this demo pipeline repeatable, but do not use it on tables containing production data.

## Metabase
In Metabase, open **Data → Databases → ETL Pipeline → Sync database schema** after the pipeline succeeds. You should then be able to explore `fact_sales` and the dimension tables.

Example metrics:
- Total revenue: `SUM(sales_amount)`
- Units sold: `SUM(quantity)`
- Orders: `COUNT(DISTINCT order_id)`
- Revenue by month: group by `dim_date.year` and `dim_date.month`
