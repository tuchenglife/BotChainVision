"""Category-based reference P/E for fair value."""

from __future__ import annotations

from src.config import load_categories

_DEFAULT_PE = 18.0


def reference_pe_map() -> dict[str, float]:
    result: dict[str, float] = {}
    for cat in load_categories():
        result[cat["id"]] = float(cat.get("reference_pe", _DEFAULT_PE))
    return result


def reference_pe_for_category(category_id: str | None) -> float:
    if not category_id:
        return _DEFAULT_PE
    return reference_pe_map().get(category_id, _DEFAULT_PE)


def fair_pe_label(category_id: str | None) -> str:
    pe = reference_pe_for_category(category_id)
    return f"EPS×{pe:g}"
