"""Valuation helpers: MA deviation, fair-value reference, price tags, EPS/dividend charts."""

from __future__ import annotations

from datetime import date
from typing import Any


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


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _annual_eps(eps_rows: list[dict[str, Any]], current_year: int) -> dict[int, dict[str, Any]]:
    by_year: dict[int, list[tuple[str, float]]] = {}
    for row in eps_rows:
        pe = row.get("period_end")
        year = _parse_year(pe) if pe else _parse_year(row.get("fiscal_period"))
        if year is None:
            continue
        eps_val = row.get("eps")
        if eps_val is None:
            continue
        fp = row.get("fiscal_period") or ""
        by_year.setdefault(year, []).append((fp, float(eps_val)))

    result: dict[int, dict[str, Any]] = {}
    for year, quarters in by_year.items():
        total = sum(v for _, v in quarters)
        is_ytd = year == current_year
        through = max((fp for fp, _ in quarters if fp), default="")
        label = f"{total:.2f}累計" if is_ytd else f"{total:.2f}"
        result[year] = {
            "eps": round(total, 4),
            "eps_label": label,
            "is_ytd": is_ytd,
            "through_quarter": through if is_ytd else None,
        }
    return result


def _attributed_dividends(dividend_rows: list[dict[str, Any]]) -> dict[int, float]:
    by_year: dict[int, float] = {}
    for row in dividend_rows:
        ex = row.get("ex_date")
        if not ex:
            continue
        ex_year = _parse_year(str(ex))
        if ex_year is None:
            continue
        eps_year = ex_year - 1
        by_year[eps_year] = by_year.get(eps_year, 0.0) + float(row["cash_dividend"])
    return {y: round(v, 4) for y, v in by_year.items()}


def build_five_year_rows(
    eps_rows: list[dict[str, Any]],
    dividend_rows: list[dict[str, Any]],
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    today = as_of or date.today()
    current_year = today.year
    years = list(range(current_year - 4, current_year + 1))

    eps_map = _annual_eps(eps_rows, current_year)
    div_map = _attributed_dividends(dividend_rows)

    rows: list[dict[str, Any]] = []
    for year in years:
        eps_info = eps_map.get(year, {})
        eps = eps_info.get("eps")
        dividend = div_map.get(year)
        payout: float | None = None
        if eps and eps > 0 and dividend is not None:
            payout = round(dividend / eps * 100, 1)

        rows.append(
            {
                "year": year,
                "eps": eps,
                "dividend": dividend,
                "payout_pct": payout,
                "eps_label": eps_info.get("eps_label"),
                "is_ytd": eps_info.get("is_ytd", False),
                "through_quarter": eps_info.get("through_quarter"),
            }
        )
    return rows


def summary_caption(rows: list[dict[str, Any]]) -> str:
    ytd = next((r for r in rows if r.get("is_ytd")), None)
    if ytd and ytd.get("through_quarter"):
        return f"今年 EPS 累計截至 {ytd['through_quarter']}｜股利歸屬前一年度 EPS"
    return "股利歸屬前一年度 EPS（例：2025/7 發放 → 2024 EPS）"


def trailing_four_quarters_eps(eps_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not eps_rows:
        return {"ttm_eps": None, "quarters": [], "periods": "", "complete": False}

    unique: dict[str, dict[str, Any]] = {}
    for row in eps_rows:
        fp = row.get("fiscal_period") or row.get("period_end") or ""
        if fp and fp not in unique:
            unique[fp] = row

    ordered = sorted(unique.values(), key=lambda r: r.get("period_end") or "", reverse=True)
    last4 = ordered[:4]
    ttm = sum(float(r["eps"]) for r in last4 if r.get("eps") is not None)
    periods = " + ".join(r.get("fiscal_period", "?") for r in reversed(last4))

    return {
        "ttm_eps": round(ttm, 4) if last4 else None,
        "quarters": last4,
        "periods": periods,
        "complete": len(last4) == 4,
    }


def last_payout_ratio(fy_rows: list[dict[str, Any]]) -> float | None:
    completed = [r for r in fy_rows if not r.get("is_ytd") and r.get("payout_pct") is not None]
    if not completed:
        return None
    return float(completed[-1]["payout_pct"])


def expected_dividend_yield_pct(
    ttm_eps: float | None,
    close: float,
    payout_pct: float | None,
) -> float | None:
    if not ttm_eps or ttm_eps <= 0 or close <= 0 or payout_pct is None:
        return None
    expected_div = ttm_eps * payout_pct / 100
    return round(expected_div / close * 100, 2)
