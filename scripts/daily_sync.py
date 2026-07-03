#!/usr/bin/env python3
"""Daily market data sync — used by GitHub Actions and manual runs."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.sync import run_full_sync  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Taiwan supply chain stock data to Supabase")
    parser.add_argument(
        "--source",
        default="scheduled",
        choices=["scheduled", "manual"],
        help="Sync source label stored in DB",
    )
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=90,
        help="Days of price history to fetch per ticker",
    )
    args = parser.parse_args()

    result = run_full_sync(source=args.source, backfill_days=args.backfill_days)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
