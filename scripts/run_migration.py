#!/usr/bin/env python3
"""Apply SQL migration to Supabase (one-time setup). Requires SUPABASE_DB_PASSWORD."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "001_initial_schema.sql"


def main() -> None:
    password = os.getenv("SUPABASE_DB_PASSWORD")
    project_ref = os.getenv("SUPABASE_PROJECT_REF", "verzhajfabdmnkmedjfo")
    if not password:
        print("Set SUPABASE_DB_PASSWORD (Database password from Supabase project settings).")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("Install psycopg2-binary: pip install psycopg2-binary")
        sys.exit(1)

    sql = MIGRATION.read_text(encoding="utf-8")
    conn_str = (
        f"host=db.{project_ref}.supabase.co port=5432 dbname=postgres "
        f"user=postgres password={password} sslmode=require"
    )
    print(f"Applying migration from {MIGRATION.name} ...")
    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("Migration applied successfully.")


if __name__ == "__main__":
    main()
