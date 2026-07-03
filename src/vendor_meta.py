"""Vendor metadata: company name and categories per ticker."""

from src.config import load_categories, load_vendors
from src.symbol_resolver import resolve_yfinance_symbol


def _category_name_map() -> dict[str, str]:
    return {c["id"]: c["name"] for c in load_categories()}


def build_ticker_meta() -> dict[str, dict]:
    cat_names = _category_name_map()
    meta: dict[str, dict] = {}

    for v in load_vendors():
        sym = resolve_yfinance_symbol(
            v["ticker"], v.get("market", "TW"), v.get("yfinance_symbol")
        )
        cat_label = cat_names.get(v["category_id"], v["category_id"])
        if sym not in meta:
            meta[sym] = {"company": v["company"], "ticker_code": v["ticker"], "categories": []}
        if cat_label not in meta[sym]["categories"]:
            meta[sym]["categories"].append(cat_label)

    for entry in meta.values():
        entry["category_text"] = "、".join(entry["categories"])
    return meta


def company_for(sym: str, meta: dict[str, dict] | None = None) -> str:
    if meta is None:
        meta = build_ticker_meta()
    return meta.get(sym, {}).get("company", sym)


def categories_for(sym: str, meta: dict[str, dict] | None = None) -> str:
    if meta is None:
        meta = build_ticker_meta()
    return meta.get(sym, {}).get("category_text", "—")
