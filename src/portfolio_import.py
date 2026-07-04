from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


BROKER_FILES = {
    "fubon_realized": Path(r"D:\Tina\股務\富邦已實現損益20260704.csv"),
    "fubon_holdings": Path(r"D:\Tina\股務\富邦未實現損益20260704.csv"),
    "sinopac_realized": Path(r"D:\Tina\股務\永豐已實現損益20260704.xlsx"),
    "sinopac_holdings": Path(r"D:\Tina\股務\永豐未實現損益20260704.xlsx"),
    "sk_realized": Path(r"D:\Tina\股務\新光證交易紀錄_已實現損益0703.csv"),
    "sk_holdings": Path(r"D:\Tina\股務\新光證庫存_0703.csv"),
}


def clean_number(value: Any, pct: bool = False, ratio_to_pct: bool = False) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "nan", "NaN", "None"}:
        return None
    if text.endswith("%"):
        text = text[:-1]
    try:
        num = float(text)
    except ValueError:
        return None
    if ratio_to_pct:
        num *= 100
    return round(num, 4) if pct or ratio_to_pct else num


def normalize_currency(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"台幣", "台　幣", "TWD", ""}:
        return "TWD"
    return text


def parse_trade_date(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    text = str(value).strip()
    if not text or text in {"nan", "NaN"}:
        return None
    text = text.split(" ")[0]
    parts = re.split(r"[/-]", text)
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        year, month, day = [int(p) for p in parts]
        if year < 1911:
            year += 1911
        return date(year, month, day).isoformat()
    return pd.to_datetime(text).date().isoformat()


def snapshot_date_from_filename(path: Path, default_year: int = 2026) -> str:
    match = re.search(r"(20\d{6})", path.name)
    if match:
        raw = match.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    match = re.search(r"(?<!\d)(\d{4})(?!\d)", path.name)
    if match:
        raw = match.group(1)
        return f"{default_year}-{raw[:2]}-{raw[2:]}"
    return date.today().isoformat()


def split_label(value: Any) -> tuple[str, str]:
    text = str(value or "").strip()
    match = re.match(r"^(.*?)\(([^)]+)\)$", text)
    if not match:
        return "", text
    return normalize_symbol(match.group(2), match.group(1)), match.group(1)


def normalize_symbol(value: Any, stock_name: str = "") -> str:
    text = str(value or "").strip()
    if not text or text == "nan":
        return ""
    text = text.upper()
    if re.fullmatch(r"\d+", text):
        if len(text) == 2:
            return f"00{text}"
        if len(text) == 3:
            return f"00{text}"
        return text.zfill(4) if len(text) < 4 else text
    return text


def read_csv_with_fallback(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="cp950", **kwargs)


def parse_fubon_realized(path: Path) -> list[dict[str, Any]]:
    df = read_csv_with_fallback(path, dtype=str).dropna(how="all")
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        symbol, name = split_label(row.get("股票名稱"))
        if not symbol:
            continue
        rows.append(
            {
                "broker": "富邦",
                "trade_date": parse_trade_date(row.get("交易日")),
                "symbol": symbol,
                "stock_name": name,
                "trade_type": row.get("交易類別"),
                "quantity": clean_number(row.get("股數")),
                "sell_price": clean_number(row.get("交易價格")),
                "buy_amount": clean_number(row.get("買入成本")),
                "sell_amount": clean_number(row.get("賣出所得")),
                "realized_pnl": clean_number(row.get("已實現損益")) or 0,
                "return_pct": clean_number(row.get("報酬率"), pct=True),
                "currency": "TWD",
                "source_broker_report": "富邦已實現損益",
                "source_file": path.name,
                "source_row_id": int(idx) + 1,
            }
        )
    return rows


def parse_fubon_holdings(path: Path) -> list[dict[str, Any]]:
    df = read_csv_with_fallback(path, dtype=str).dropna(how="all")
    snapshot_date = snapshot_date_from_filename(path)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        symbol, name = split_label(row.get("證券名稱"))
        if not symbol:
            continue
        rows.append(
            {
                "broker": "富邦",
                "snapshot_date": snapshot_date,
                "symbol": symbol,
                "stock_name": name,
                "position_type": row.get("類別"),
                "quantity": clean_number(row.get("即時庫存(股)")),
                "market_price": clean_number(row.get("現價")),
                "market_value": clean_number(row.get("資產市值")),
                "avg_cost_price": clean_number(row.get("成本均價")),
                "cost_basis": clean_number(row.get("付出成本")),
                "unrealized_pnl": clean_number(row.get("原幣損益試算")),
                "return_pct": clean_number(row.get("獲利率"), pct=True),
                "estimated_net_amount": clean_number(row.get("淨值")),
                "currency": normalize_currency(row.get("幣別")),
                "source_broker_report": "富邦未實現損益",
                "source_file": path.name,
                "source_row_id": int(idx) + 1,
            }
        )
    return rows


def parse_sinopac_realized(path: Path) -> list[dict[str, Any]]:
    df = pd.read_excel(path, sheet_name=0, dtype=str).dropna(how="all")
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        symbol = normalize_symbol(row.get("股票代碼"), row.get("股票名稱", ""))
        if not symbol or not str(row.get("成交日", "")).strip():
            continue
        rows.append(
            {
                "broker": "永豐",
                "trade_date": parse_trade_date(row.get("成交日")),
                "symbol": symbol,
                "stock_name": str(row.get("股票名稱", "")).strip(),
                "trade_type": row.get("交易別"),
                "quantity": clean_number(row.get("成交數量")),
                "sell_price": clean_number(row.get("成交價格")),
                "buy_amount": clean_number(row.get("買進金額")),
                "sell_amount": clean_number(row.get("賣出金額")),
                "realized_pnl": clean_number(row.get("損益")) or 0,
                "return_pct": clean_number(row.get("報酬率"), ratio_to_pct=True),
                "order_id": row.get("委託單號"),
                "currency": normalize_currency(row.get("幣別")),
                "source_broker_report": "永豐已實現損益",
                "source_file": path.name,
                "source_row_id": int(idx) + 1,
            }
        )
    return rows


def parse_sinopac_holdings(path: Path) -> list[dict[str, Any]]:
    df = pd.read_excel(path, sheet_name=0, dtype=str).dropna(how="all")
    snapshot_date = snapshot_date_from_filename(path)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        symbol = normalize_symbol(row.get("代碼"), row.get("股票名稱", ""))
        if not symbol:
            continue
        rows.append(
            {
                "broker": "永豐",
                "snapshot_date": snapshot_date,
                "symbol": symbol,
                "stock_name": str(row.get("股票名稱", "")).strip(),
                "position_type": row.get("類別"),
                "quantity": clean_number(row.get("昨日餘額")),
                "market_price": clean_number(row.get("現價")),
                "market_value": clean_number(row.get("現值")),
                "avg_cost_price": clean_number(row.get("成本均價")),
                "cost_basis": clean_number(row.get("付出成本")),
                "unrealized_pnl": clean_number(row.get("損益試算")),
                "return_pct": clean_number(row.get("獲利率"), ratio_to_pct=True),
                "estimated_net_amount": clean_number(row.get("現值")),
                "currency": normalize_currency(row.get("幣別")),
                "source_broker_report": "永豐未實現損益",
                "source_file": path.name,
                "source_row_id": int(idx) + 1,
            }
        )
    return rows


def parse_sk_realized(path: Path) -> list[dict[str, Any]]:
    df = read_csv_with_fallback(path, skiprows=3, dtype=str, engine="python").dropna(how="all")
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        symbol = normalize_symbol(row.get("代號"), row.get("股票", ""))
        if not symbol or not str(row.get("成交日期", "")).strip():
            continue
        net_amount = clean_number(row.get("淨收付"))
        pnl = clean_number(row.get("損益")) or 0
        rows.append(
            {
                "broker": "新光",
                "trade_date": parse_trade_date(row.get("成交日期")),
                "symbol": symbol,
                "stock_name": str(row.get("股票", "")).strip(),
                "trade_type": row.get("類別"),
                "quantity": clean_number(row.get("成交股數")),
                "sell_price": clean_number(row.get("單價")),
                "buy_amount": (net_amount - pnl) if net_amount is not None else None,
                "sell_amount": clean_number(row.get("價金")),
                "fee": clean_number(row.get("手續費")),
                "tax": clean_number(row.get("交易稅")),
                "net_amount": net_amount,
                "realized_pnl": pnl,
                "return_pct": clean_number(row.get("報酬率"), pct=True),
                "order_id": row.get("委託書號"),
                "currency": normalize_currency(row.get("幣別")),
                "source_broker_report": "新光已實現損益",
                "source_file": path.name,
                "source_row_id": int(idx) + 1,
            }
        )
    return rows


def parse_sk_holdings(path: Path) -> list[dict[str, Any]]:
    df = read_csv_with_fallback(path, skiprows=3, dtype=str, engine="python").dropna(how="all")
    snapshot_date = snapshot_date_from_filename(path)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        symbol = normalize_symbol(row.get("股號"), row.get("商品", ""))
        if not symbol:
            continue
        rows.append(
            {
                "broker": "新光",
                "snapshot_date": snapshot_date,
                "symbol": symbol,
                "stock_name": str(row.get("商品", "")).strip(),
                "position_type": row.get("類別"),
                "quantity": clean_number(row.get("股數")),
                "available_quantity": clean_number(row.get("可用股數")),
                "market_price": clean_number(row.get("市價")),
                "market_value": clean_number(row.get("市值")),
                "avg_cost_price": clean_number(row.get("成本價")),
                "trade_avg_price": clean_number(row.get("成交均價")),
                "cost_basis": clean_number(row.get("成本")),
                "unrealized_pnl": clean_number(row.get("預估損益")),
                "return_pct": clean_number(row.get("報酬率(%)"), pct=True),
                "estimated_net_amount": clean_number(row.get("預估淨收付")),
                "fee_estimate": clean_number(row.get("手續費")),
                "currency": normalize_currency(row.get("幣別")),
                "source_broker_report": "新光庫存",
                "source_file": path.name,
                "source_row_id": int(idx) + 1,
            }
        )
    return rows


def parse_default_files(paths: dict[str, Path] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = paths or BROKER_FILES
    realized: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []

    parsers: Iterable[tuple[str, str, Any]] = [
        ("fubon_realized", "realized", parse_fubon_realized),
        ("fubon_holdings", "holdings", parse_fubon_holdings),
        ("sinopac_realized", "realized", parse_sinopac_realized),
        ("sinopac_holdings", "holdings", parse_sinopac_holdings),
        ("sk_realized", "realized", parse_sk_realized),
        ("sk_holdings", "holdings", parse_sk_holdings),
    ]
    for key, kind, parser in parsers:
        path = files.get(key)
        if not path or not path.exists():
            continue
        parsed = parser(path)
        if kind == "realized":
            realized.extend(parsed)
        else:
            holdings.extend(parsed)
    return realized, holdings
