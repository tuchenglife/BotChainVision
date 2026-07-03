"""Fundamental metrics from yfinance."""

from __future__ import annotations

import yfinance as yf


def fetch_pe_metrics(yfinance_symbol: str, close_price: float | None = None) -> dict:
    ext = fetch_extended_fundamentals(yfinance_symbol, close_price)
    return {
        "pe_ratio": ext.get("pe_ratio"),
        "eps_ttm": ext.get("eps_ttm"),
    }


def fetch_extended_fundamentals(yfinance_symbol: str, close_price: float | None = None) -> dict:
    try:
        info = yf.Ticker(yfinance_symbol).info or {}
    except Exception:
        info = {}

    pe = info.get("trailingPE")
    eps = info.get("trailingEps")
    roe = info.get("returnOnEquity")
    low52 = info.get("fiftyTwoWeekLow")
    high52 = info.get("fiftyTwoWeekHigh")
    target = info.get("targetMeanPrice")

    if pe is None and eps and float(eps) > 0 and close_price:
        pe = float(close_price) / float(eps)

    def _f(v, decimals=2):
        if v is None:
            return None
        try:
            return round(float(v), decimals)
        except (TypeError, ValueError):
            return None

    return {
        "pe_ratio": _f(pe),
        "eps_ttm": _f(eps, 4),
        "roe": _f(roe, 4),
        "roe_pct": _f(roe * 100 if roe is not None else None, 2),
        "week52_low": _f(low52),
        "week52_high": _f(high52),
        "target_price": _f(target),
    }
