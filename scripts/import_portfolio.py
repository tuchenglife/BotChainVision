#!/usr/bin/env python3
"""Import local broker export files into Supabase portfolio tables."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_client, upsert_rows
from src.portfolio_import import parse_default_files


def main() -> None:
    load_dotenv()
    client = get_client()
    realized, holdings = parse_default_files()

    upsert_rows(
        client,
        "portfolio_realized_trades",
        realized,
        on_conflict="broker,source_file,source_row_id",
    )
    upsert_rows(
        client,
        "portfolio_holdings",
        holdings,
        on_conflict="broker,source_file,source_row_id",
    )

    realized_total = sum(float(r.get("realized_pnl") or 0) for r in realized)
    holdings_total = sum(float(r.get("unrealized_pnl") or 0) for r in holdings)
    market_total = sum(float(r.get("market_value") or 0) for r in holdings)

    print(f"Imported realized rows: {len(realized)}; total pnl: {realized_total:,.0f}")
    print(f"Imported holding rows: {len(holdings)}; unrealized pnl: {holdings_total:,.0f}")
    print(f"Imported holding market value: {market_total:,.0f}")


if __name__ == "__main__":
    main()
