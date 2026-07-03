"""Resolve yfinance symbol for Taiwan stocks — no network calls (safe for Streamlit startup)."""

from __future__ import annotations

from src.config import load_vendors, to_yfinance_symbol

# Verified via yfinance testing (TW vs TWO)
_KNOWN: dict[str, str] = {
    "1597": "1597.TW",
    "4576": "4576.TW",
    "4571": "4571.TW",
    "1536": "1536.TW",
    "6215": "6215.TW",
    "5371": "5371.TWO",
    "3362": "3362.TWO",
    "4510": "4510.TWO",
}

_RESOLVED: dict[str, str] = {}


def resolve_yfinance_symbol(ticker: str, market: str = "TW", yfinance_symbol: str | None = None) -> str:
    """Map numeric ticker to yfinance symbol using settings override or known table."""
    if yfinance_symbol:
        return yfinance_symbol
    if ticker in _RESOLVED:
        return _RESOLVED[ticker]
    if ticker in _KNOWN:
        sym = _KNOWN[ticker]
        _RESOLVED[ticker] = sym
        return sym
    sym = to_yfinance_symbol(ticker, market)
    _RESOLVED[ticker] = sym
    return sym


def unique_resolved_tickers(vendors: list[dict] | None = None) -> list[str]:
    if vendors is None:
        vendors = load_vendors()
    seen: set[str] = set()
    result: list[str] = []
    for v in vendors:
        sym = resolve_yfinance_symbol(
            v["ticker"],
            v.get("market", "TW"),
            v.get("yfinance_symbol"),
        )
        if sym not in seen:
            seen.add(sym)
            result.append(sym)
    return result
