"""EPS / dividend chart helpers (colocated with Streamlit entry for reliable Cloud deploy)."""

from __future__ import annotations

from datetime import date
from typing import Any


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _quarterly_rows(eps_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in eps_rows if r.get("period_type", "quarterly") == "quarterly"]


def _annual_eps(eps_rows: list[dict[str, Any]], current_year: int) -> dict[int, dict[str, Any]]:
    annual_by_year: dict[int, float] = {}
    for row in eps_rows:
        if row.get("period_type") != "annual":
            continue
        year = _parse_year(row.get("fiscal_period")) or _parse_year(row.get("period_end"))
        if year is None or row.get("eps") is None:
            continue
        annual_by_year[year] = float(row["eps"])

    by_year: dict[int, list[tuple[str, float]]] = {}
    for row in _quarterly_rows(eps_rows):
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
    years = set(annual_by_year) | set(by_year) | {current_year}
    for year in sorted(years):
        if year == current_year and year in by_year:
            quarters = by_year[year]
            total = sum(v for _, v in quarters)
            through = max((fp for fp, _ in quarters if fp), default="")
            result[year] = {
                "eps": round(total, 4),
                "eps_label": f"{total:.2f}累計",
                "is_ytd": True,
                "through_quarter": through or None,
            }
        elif year < current_year and year in annual_by_year:
            eps = annual_by_year[year]
            result[year] = {
                "eps": round(eps, 4),
                "eps_label": f"{eps:.2f}",
                "is_ytd": False,
                "through_quarter": None,
            }
        elif year in by_year:
            quarters = by_year[year]
            total = sum(v for _, v in quarters)
            through = max((fp for fp, _ in quarters if fp), default="")
            is_ytd = year == current_year
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
    quarterly = _quarterly_rows(eps_rows)
    if not quarterly:
        return {"ttm_eps": None, "quarters": [], "periods": "", "complete": False}

    unique: dict[str, dict[str, Any]] = {}
    for row in quarterly:
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


def ttm_gap_caption(ttm: dict[str, Any]) -> str | None:
    if ttm.get("complete"):
        return None
    n = len(ttm.get("quarters") or [])
    missing = 4 - n
    return (
        f"目前僅 {n} 季可加總（尚缺 {missing} 季）。"
        "yfinance 季度 EPS 常缺最新季或 Q4 空值，2026 季度可能尚未更新；"
        "五年圖表之歷年 EPS 來自年度財報。"
    )


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
