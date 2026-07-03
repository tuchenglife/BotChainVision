from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from src.config import load_categories, load_vendors
from src.db import fetch_max_trade_date, get_client, log_sync, upsert_rows
from src.fundamentals import fetch_pe_metrics
from src.indicators import enrich_price_dataframe
from src.symbol_resolver import resolve_yfinance_symbol, unique_resolved_tickers

# Long-term accumulation: initial backfill 2y; daily incremental keeps older rows in DB.
INITIAL_BACKFILL_DAYS = 730
MA_BUFFER_DAYS = 90
DAILY_MIN_FETCH_DAYS = 120


def _str_or_none(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return str(val) if val != "nan" else None


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    idx = df.index
    if getattr(idx, "tz", None) is not None:
        df = df.copy()
        df.index = idx.tz_localize(None)
    return df


def fetch_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """Fetch OHLCV; uses start date for windows longer than 730 days."""
    t = yf.Ticker(ticker)
    if days > 730:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = t.history(start=start, auto_adjust=True)
    else:
        df = t.history(period=f"{days}d", auto_adjust=True)
    return _normalize_index(df)


def _resolve_fetch_days(client, ticker: str, backfill_days: int) -> int:
    """Smart fetch window: accumulate history without re-downloading everything daily."""
    max_date = fetch_max_trade_date(client, ticker)
    if max_date is None:
        return max(backfill_days, INITIAL_BACKFILL_DAYS)
    days_since = (date.today() - max_date).days
    return max(DAILY_MIN_FETCH_DAYS, days_since + MA_BUFFER_DAYS, backfill_days)


def sync_supply_chain_settings(client) -> None:
    categories = [
        {
            "id": c["id"],
            "name": c["name"],
            "component_examples": c.get("component_examples", ""),
        }
        for c in load_categories()
    ]
    upsert_rows(client, "supply_chain_categories", categories, on_conflict="id")

    vendors = [
        {
            "category_id": v["category_id"],
            "company": v["company"],
            "ticker": v["ticker"],
            "market": v.get("market", "TW"),
            "watch": v.get("watch", True),
            "notes": v.get("notes", ""),
        }
        for v in load_vendors(watch_only=False)
    ]
    upsert_rows(client, "supply_chain_vendors", vendors, on_conflict="category_id,ticker")


def sync_daily_prices(
    client,
    tickers: list[str] | None = None,
    source: str = "scheduled",
    backfill_days: int = 90,
) -> dict[str, Any]:
    if tickers is None:
        tickers = unique_resolved_tickers()
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for ticker in tickers:
        try:
            fetch_days = _resolve_fetch_days(client, ticker, backfill_days)
            df = fetch_history(ticker, days=fetch_days)
            if df.empty:
                errors.append(f"{ticker}: no data")
                continue

            df = enrich_price_dataframe(df.sort_index())
            latest_close = float(df["Close"].iloc[-1])
            metrics = fetch_pe_metrics(ticker, close_price=latest_close)
            eps_ttm = metrics.get("eps_ttm")

            for ts, row in df.iterrows():
                trade_date = ts.date() if hasattr(ts, "date") else ts
                close_price = float(row["Close"])
                pe_ratio = None
                if eps_ttm and eps_ttm > 0:
                    pe_ratio = round(close_price / eps_ttm, 2)
                elif ts == df.index[-1]:
                    pe_ratio = metrics.get("pe_ratio")

                rows.append(
                    {
                        "ticker": ticker,
                        "trade_date": trade_date.isoformat(),
                        "open_price": float(row["Open"]) if pd.notna(row["Open"]) else None,
                        "high_price": float(row["High"]),
                        "low_price": float(row["Low"]),
                        "close_price": close_price,
                        "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                        "ma5": float(row["ma5"]) if pd.notna(row.get("ma5")) else None,
                        "ma20": float(row["ma20"]) if pd.notna(row.get("ma20")) else None,
                        "ma60": float(row["ma60"]) if pd.notna(row.get("ma60")) else None,
                        "signal_short": _str_or_none(row.get("signal_short")),
                        "signal_medium": _str_or_none(row.get("signal_medium")),
                        "pe_ratio": pe_ratio,
                        "eps_ttm": eps_ttm,
                        "source": source,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{ticker}: {exc}")

    chunk_size = 500
    for i in range(0, len(rows), chunk_size):
        upsert_rows(client, "daily_prices", rows[i : i + chunk_size], on_conflict="ticker,trade_date")
    return {"rows": len(rows), "errors": errors}


def sync_dividends(client, tickers: list[str] | None = None) -> list[dict[str, Any]]:
    if tickers is None:
        tickers = unique_resolved_tickers()
    rows: list[dict[str, Any]] = []

    for ticker in tickers:
        try:
            divs = yf.Ticker(ticker).dividends
            if divs is None or divs.empty:
                continue
            divs = _normalize_index(divs.to_frame(name="cash_dividend"))
            for ts, row in divs.iterrows():
                ex_date = ts.date() if hasattr(ts, "date") else ts
                rows.append(
                    {
                        "ticker": ticker,
                        "ex_date": ex_date.isoformat(),
                        "cash_dividend": float(row["cash_dividend"]),
                        "fiscal_year": ex_date.year,
                        "source_type": "yfinance",
                    }
                )
        except Exception:
            continue

    upsert_rows(client, "dividends", rows, on_conflict="ticker,ex_date")
    return rows


def _trailing_12m_dividend(client, ticker: str, as_of: date) -> float:
    start = (as_of - timedelta(days=365)).isoformat()
    end = as_of.isoformat()
    result = (
        client.table("dividends")
        .select("cash_dividend")
        .eq("ticker", ticker)
        .gte("ex_date", start)
        .lte("ex_date", end)
        .execute()
    )
    rows = result.data or []
    return sum(float(r["cash_dividend"]) for r in rows)


def sync_dividend_yields(
    client,
    tickers: list[str] | None = None,
    source: str = "scheduled",
) -> list[dict[str, Any]]:
    if tickers is None:
        tickers = unique_resolved_tickers()
    rows: list[dict[str, Any]] = []

    for ticker in tickers:
        latest = (
            client.table("daily_prices")
            .select("trade_date, close_price")
            .eq("ticker", ticker)
            .order("trade_date", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not latest:
            continue
        trade_date = date.fromisoformat(latest[0]["trade_date"])
        close_price = float(latest[0]["close_price"])
        trailing = _trailing_12m_dividend(client, ticker, trade_date)
        yield_pct = (trailing / close_price * 100) if close_price > 0 else None
        rows.append(
            {
                "ticker": ticker,
                "trade_date": trade_date.isoformat(),
                "close_price": close_price,
                "trailing_12m_div": trailing,
                "dividend_yield_pct": round(yield_pct, 4) if yield_pct is not None else None,
                "source": source,
            }
        )

    upsert_rows(client, "dividend_yield_daily", rows, on_conflict="ticker,trade_date")
    return rows


def sync_historical_eps(client, tickers: list[str] | None = None) -> list[dict[str, Any]]:
    if tickers is None:
        tickers = unique_resolved_tickers()
    rows: list[dict[str, Any]] = []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            income = t.quarterly_income_stmt
            if income is not None and not income.empty and "Basic EPS" in income.index:
                eps_row = income.loc["Basic EPS"]
                for period_end, eps_val in eps_row.items():
                    if pd.isna(eps_val):
                        continue
                    pe = period_end.date() if hasattr(period_end, "date") else period_end
                    fiscal_period = f"{pe.year}Q{(pe.month - 1) // 3 + 1}"
                    rows.append(
                        {
                            "ticker": ticker,
                            "period_type": "quarterly",
                            "fiscal_period": fiscal_period,
                            "period_end": pe.isoformat(),
                            "eps": float(eps_val),
                            "source_type": "yfinance",
                        }
                    )
        except Exception:
            continue

    upsert_rows(client, "historical_eps", rows, on_conflict="ticker,period_type,fiscal_period")
    return rows


def run_full_sync(source: str = "scheduled", backfill_days: int = 90) -> dict[str, Any]:
    client = get_client()
    tickers = unique_resolved_tickers()
    try:
        sync_supply_chain_settings(client)
        price_result = sync_daily_prices(client, tickers, source=source, backfill_days=backfill_days)
        sync_dividends(client, tickers)
        sync_dividend_yields(client, tickers, source=source)
        sync_historical_eps(client, tickers)
        err_msg = "; ".join(price_result.get("errors", []))
        status = "ok" if price_result.get("rows", 0) > 0 else "error"
        log_sync(
            client,
            sync_type="full",
            source=source,
            tickers_count=len(tickers),
            status=status,
            message=f"Prices: {price_result.get('rows', 0)} rows. {err_msg}".strip(),
        )
        if status == "error":
            raise RuntimeError(err_msg or "No price data synced")
        return {
            "status": "ok",
            "tickers_count": len(tickers),
            "price_rows": price_result.get("rows", 0),
            "errors": price_result.get("errors", []),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
        }
    except Exception as exc:  # noqa: BLE001
        log_sync(
            client,
            sync_type="full",
            source=source,
            tickers_count=len(tickers),
            status="error",
            message=str(exc),
        )
        raise
