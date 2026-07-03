"""Valuation helpers: MA deviation, fair-value reference, price tags."""

from __future__ import annotations


def pct_vs(value: float | None, base: float | None) -> float | None:
    if value is None or base is None or base == 0:
        return None
    return round((value - base) / base * 100, 2)


def fair_value_by_eps(eps: float | None, reference_pe: float = 15.0) -> float | None:
    if eps is None or eps <= 0:
        return None
    return round(eps * reference_pe, 2)


def fair_value_52w_mid(low: float | None, high: float | None) -> float | None:
    if low is None or high is None:
        return None
    return round((low + high) / 2, 2)


def ma_position_label(vs_ma20: float | None, vs_ma60: float | None) -> str:
    if vs_ma20 is None and vs_ma60 is None:
        return "—"
    below20 = vs_ma20 is not None and vs_ma20 < -3
    below60 = vs_ma60 is not None and vs_ma60 < -3
    above20 = vs_ma20 is not None and vs_ma20 > 3
    above60 = vs_ma60 is not None and vs_ma60 > 3
    if below20 and below60:
        return "低於均線"
    if above20 and above60:
        return "高於均線"
    if below20:
        return "低於MA20"
    if above20:
        return "高於MA20"
    return "均線附近"


def price_assessment(
    close: float | None,
    pe: float | None,
    vs_ma20: float | None,
    vs_ma60: float | None,
    fair_eps: float | None,
    roe: float | None,
    reference_pe: float = 18.0,
) -> str:
    """Heuristic tag: 偏低 / 合理 / 偏高 (not investment advice)."""
    if close is None:
        return "—"
    score = 0
    if fair_eps and close < fair_eps * 0.92:
        score -= 1
    elif fair_eps and close > fair_eps * 1.12:
        score += 1
    if vs_ma20 is not None and vs_ma20 < -8:
        score -= 1
    elif vs_ma20 is not None and vs_ma20 > 8:
        score += 1
    if vs_ma60 is not None and vs_ma60 < -8:
        score -= 1
    elif vs_ma60 is not None and vs_ma60 > 8:
        score += 1
    if pe is not None:
        low_pe = reference_pe * 0.75
        high_pe = reference_pe * 1.25
        if pe < low_pe:
            score -= 1
        elif pe > high_pe:
            score += 1
    if roe is not None and roe > 0.15 and score <= 0:
        score -= 1
    if score <= -2:
        return "偏低"
    if score >= 2:
        return "偏高"
    return "合理"


def assessment_style(tag: str | None) -> str:
    if tag == "偏低":
        return "color: #22c55e; font-weight: bold"
    if tag == "偏高":
        return "color: #ef4444; font-weight: bold"
    if tag == "合理":
        return "color: #94a3b8"
    return ""
