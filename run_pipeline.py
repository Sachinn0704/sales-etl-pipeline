"""Run the complete local-CSV -> PostgreSQL sales ETL pipeline."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(script):
    print(f"\n=== Running {script} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)


def main():
    run("ingest.py")
    run("build_star.py")
    run("checks.py")
    print("\nETL pipeline completed successfully.")


if __name__ == "__main__":
    main()
