#!/usr/bin/env python3
"""Apply all SQL migrations in supabase/migrations/. Requires SUPABASE_DB_PASSWORD."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"


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

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migration files found.")
        sys.exit(1)

    conn_str = (
        f"host=db.{project_ref}.supabase.co port=5432 dbname=postgres "
        f"user=postgres password={password} sslmode=require"
    )
    with psycopg2.connect(conn_str) as conn:
        with conn.cursor() as cur:
            for path in files:
                print(f"Applying {path.name} ...")
                try:
                    cur.execute(path.read_text(encoding="utf-8"))
                except psycopg2.Error as exc:
                    if exc.pgcode == "42710":  # duplicate_object (policy etc.)
                        print(f"  Skipped (already applied): {exc.pgerror.strip()}")
                        conn.rollback()
                        continue
                    raise
        conn.commit()
    print(f"Applied {len(files)} migration(s) successfully.")


if __name__ == "__main__":
    main()
