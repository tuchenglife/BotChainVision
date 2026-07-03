"""Moving-average crossover signals."""

from __future__ import annotations

import pandas as pd


def ma_cross_status(
    short_prev: float | None,
    long_prev: float | None,
    short_curr: float | None,
    long_curr: float | None,
) -> str | None:
    """Return crossover event or current trend (多頭/空頭)."""
    vals = [short_prev, long_prev, short_curr, long_curr]
    if any(v is None or (isinstance(v, float) and pd.isna(v)) for v in vals):
        return None
    if short_prev <= long_prev and short_curr > long_curr:
        return "黃金交叉"
    if short_prev >= long_prev and short_curr < long_curr:
        return "死亡交叉"
    if short_curr > long_curr:
        return "多頭"
    if short_curr < long_curr:
        return "空頭"
    return "—"


def enrich_price_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add MA columns and short/medium status to OHLCV dataframe (sorted ascending)."""
    out = df.copy()
    out["ma5"] = out["Close"].rolling(window=5).mean()
    out["ma20"] = out["Close"].rolling(window=20).mean()
    out["ma60"] = out["Close"].rolling(window=60).mean()

    signal_short: list[str | None] = [None]
    signal_medium: list[str | None] = [None]

    for i in range(1, len(out)):
        prev = out.iloc[i - 1]
        curr = out.iloc[i]
        signal_short.append(
            ma_cross_status(prev["ma5"], prev["ma20"], curr["ma5"], curr["ma20"])
        )
        signal_medium.append(
            ma_cross_status(prev["ma20"], prev["ma60"], curr["ma20"], curr["ma60"])
        )

    out["signal_short"] = signal_short
    out["signal_medium"] = signal_medium
    return out
