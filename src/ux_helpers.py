"""Category helpers for UX grouping."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import load_categories, load_vendors
from src.symbol_resolver import resolve_yfinance_symbol

TW = ZoneInfo("Asia/Taipei")


def format_tw_datetime(iso_str: str | None) -> str:
    """Format UTC/offset ISO timestamp for display in Taiwan time."""
    if not iso_str:
        return "—"
    text = iso_str.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return iso_str[:19]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TW).strftime("%Y-%m-%d %H:%M")


def category_options() -> list[dict]:
    return load_categories()


def category_short_name(full_name: str) -> str:
    if "(" in full_name:
        return full_name.split("(")[0].strip()
    return full_name


def tickers_in_category(category_id: str | None, meta: dict) -> list[str]:
    if category_id is None or category_id == "all":
        return sorted(meta.keys())
    cat_names = {c["id"]: c["name"] for c in load_categories()}
    target = cat_names.get(category_id, "")
    result = []
    for sym, m in meta.items():
        if target in m.get("categories", []):
            result.append(sym)
    return sorted(result)


def primary_category_id(sym: str, meta: dict) -> str | None:
    ids = meta.get(sym, {}).get("category_ids", [])
    return ids[0] if ids else None


def primary_category(sym: str, meta: dict) -> str:
    cats = meta.get(sym, {}).get("categories", [])
    if not cats:
        return "—"
    return category_short_name(cats[0])


def ticker_select_label(sym: str, meta: dict) -> str:
    m = meta.get(sym, {})
    company = m.get("company", sym)
    cat = primary_category(sym, meta)
    code = m.get("ticker_code", "")
    return f"{company}（{code}）｜{cat}"
