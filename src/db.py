from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from supabase import Client, create_client

from src.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. "
            "Set them in .env locally or GitHub Secrets for Actions."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def upsert_rows(client: Client, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        return
    client.table(table).upsert(rows, on_conflict=on_conflict).execute()


def log_sync(
    client: Client,
    sync_type: str,
    source: str,
    tickers_count: int,
    status: str,
    message: str = "",
) -> None:
    client.table("sync_log").insert(
        {
            "sync_type": sync_type,
            "source": source,
            "tickers_count": tickers_count,
            "status": status,
            "message": message,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


def fetch_all(client: Client, table: str, order_by: str | None = None, desc: bool = True) -> list[dict]:
    query = client.table(table).select("*")
    if order_by:
        query = query.order(order_by, desc=desc)
    return query.execute().data or []


def fetch_prices(client: Client, ticker: str, limit: int = 365) -> list[dict]:
    return (
        client.table("daily_prices")
        .select("*")
        .eq("ticker", ticker)
        .order("trade_date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def fetch_yields(client: Client, ticker: str, limit: int = 365) -> list[dict]:
    return (
        client.table("dividend_yield_daily")
        .select("*")
        .eq("ticker", ticker)
        .order("trade_date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def fetch_dividends(client: Client, ticker: str) -> list[dict]:
    return (
        client.table("dividends")
        .select("*")
        .eq("ticker", ticker)
        .order("ex_date", desc=True)
        .execute()
        .data
        or []
    )


def fetch_eps(client: Client, ticker: str) -> list[dict]:
    return (
        client.table("historical_eps")
        .select("*")
        .eq("ticker", ticker)
        .order("period_end", desc=True)
        .execute()
        .data
        or []
    )


def latest_sync(client: Client) -> dict | None:
    rows = (
        client.table("sync_log")
        .select("*")
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def to_date_str(d: date | datetime) -> str:
    if isinstance(d, datetime):
        return d.date().isoformat()
    return d.isoformat()
