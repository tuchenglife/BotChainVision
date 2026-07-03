"""Resolve working yfinance symbol for Taiwan stocks (TW vs TWO)."""

from __future__ import annotations

import yfinance as yf

from src.config import to_yfinance_symbol

# ticker -> working yfinance symbol (populated at runtime)
_RESOLVED: dict[str, str] = {}


def _has_data(symbol: str) -> bool:
    try:
        df = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
        return df is not None and not df.empty
    except Exception:
        return False


def resolve_yfinance_symbol(ticker: str, market: str = "TW") -> str:
    """Return yfinance symbol that returns price data; tries TW and TWO."""
    cache_key = ticker
    if cache_key in _RESOLVED:
        return _RESOLVED[cache_key]

    candidates: list[str] = []
    primary = to_yfinance_symbol(ticker, market)
    candidates.append(primary)
    for suffix in ("TW", "TWO"):
        sym = f"{ticker}.{suffix}"
        if sym not in candidates:
            candidates.append(sym)

    for sym in candidates:
        if _has_data(sym):
            _RESOLVED[cache_key] = sym
            return sym

    _RESOLVED[cache_key] = primary
    return primary


def unique_resolved_tickers(vendors: list[dict] | None = None) -> list[str]:
    from src.config import load_vendors

    if vendors is None:
        vendors = load_vendors()
    seen: set[str] = set()
    result: list[str] = []
    for v in vendors:
        sym = resolve_yfinance_symbol(v["ticker"], v.get("market", "TW"))
        if sym not in seen:
            seen.add(sym)
            result.append(sym)
    return result
