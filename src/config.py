import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = ROOT_DIR / "settings"


def _get_secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return ""


SUPABASE_URL = _get_secret("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = _get_secret("SUPABASE_SERVICE_ROLE_KEY")


def load_json(filename: str) -> dict:
    path = SETTINGS_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_vendors(watch_only: bool = True) -> list[dict]:
    vendors = load_json("supply_chain_vendors.json")["vendors"]
    if watch_only:
        vendors = [v for v in vendors if v.get("watch", True)]
    return vendors


def load_categories() -> list[dict]:
    return load_json("supply_chain_categories.json")["categories"]


def to_yfinance_symbol(ticker: str, market: str = "TW") -> str:
    suffix = market.upper()
    if suffix not in ("TW", "TWO"):
        suffix = "TW"
    return f"{ticker}.{suffix}"


def unique_watch_tickers(vendors: list[dict] | None = None) -> list[str]:
    if vendors is None:
        vendors = load_vendors()
    seen: set[str] = set()
    result: list[str] = []
    for v in vendors:
        sym = to_yfinance_symbol(v["ticker"], v.get("market", "TW"))
        if sym not in seen:
            seen.add(sym)
            result.append(sym)
    return result
