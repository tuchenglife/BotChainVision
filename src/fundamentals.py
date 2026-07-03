"""Fundamental metrics: P/E ratio from yfinance."""

from __future__ import annotations

import yfinance as yf


def fetch_pe_metrics(yfinance_symbol: str, close_price: float | None = None) -> dict:
    """
    Return trailing P/E and EPS.
    Falls back to close / trailingEps when trailingPE is missing.
    """
    try:
        info = yf.Ticker(yfinance_symbol).info or {}
    except Exception:
        info = {}

    pe = info.get("trailingPE")
    eps = info.get("trailingEps")

    if pe is None and eps and float(eps) > 0 and close_price:
        pe = float(close_price) / float(eps)

    if pe is not None:
        try:
            pe = round(float(pe), 2)
        except (TypeError, ValueError):
            pe = None

    if eps is not None:
        try:
            eps = round(float(eps), 4)
        except (TypeError, ValueError):
            eps = None

    return {"pe_ratio": pe, "eps_ttm": eps}
