"""Load seed/seed.sql verbatim, in one transaction, only if `accounts` is empty."""

import os
from pathlib import Path

import psycopg

SEED_SQL = Path(__file__).resolve().parents[1] / "seed" / "seed.sql"
DEFAULT_URL = "postgresql://app:app@localhost:5432/app"


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    # `with connect()` commits on success and rolls back on error: one transaction.
    with psycopg.connect(url) as conn:
        row = conn.execute("SELECT EXISTS (SELECT 1 FROM accounts)").fetchone()
        if row is not None and row[0]:
            print("seed: accounts is not empty, skipped loading seed/seed.sql")
            return
        conn.execute(SEED_SQL.read_bytes())
    print(f"seed: loaded {SEED_SQL.name}")


if __name__ == "__main__":
    main()
