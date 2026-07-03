import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_categories, load_vendors, to_yfinance_symbol, unique_watch_tickers
from src.db import (
    fetch_dividends,
    fetch_eps,
    fetch_prices,
    fetch_yields,
    get_client,
    latest_sync,
)
from src.sync import run_full_sync

st.set_page_config(
    page_title="BotChainVision",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 BotChainVision")
st.caption("人形機器人關鍵零組件 × 台股供應鏈追蹤")


@st.cache_resource
def db_client():
    return get_client()


def render_refresh_bar():
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        refresh = st.button("🔄 立即更新股價與殖利率", type="primary", use_container_width=True)
    with col2:
        backfill = st.selectbox("回補天數", [30, 90, 180, 365], index=1, label_visibility="collapsed")
    with col3:
        try:
            last = latest_sync(db_client())
            if last:
                st.caption(
                    f"上次同步：{last.get('finished_at', '')[:19]} "
                    f"({last.get('source', '')} / {last.get('status', '')})"
                )
            else:
                st.caption("尚未同步過資料")
        except Exception as exc:  # noqa: BLE001
            st.caption(f"無法讀取同步紀錄：{exc}")

    if refresh:
        with st.spinner("更新中…（yfinance → Supabase）"):
            try:
                result = run_full_sync(source="manual", backfill_days=int(backfill))
                st.success(f"已更新 {result['tickers_count']} 檔標的")
                st.cache_data.clear()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"更新失敗：{exc}")
                st.info("請確認已在 Supabase 執行 migration，且 .env / Secrets 設定正確。")


def render_supply_chain():
    st.subheader("供應鏈地圖")
    categories = {c["id"]: c for c in load_categories()}
    vendors = load_vendors()

    tabs = st.tabs([categories[c["id"]]["name"] for c in load_categories()])
    for tab, cat in zip(tabs, load_categories()):
        with tab:
            rows = [v for v in vendors if v["category_id"] == cat["id"]]
            st.markdown(f"**元件範例：** {cat['component_examples']}")
            df = pd.DataFrame(
                [
                    {
                        "公司": v["company"],
                        "代號": v["ticker"],
                        "YFinance": to_yfinance_symbol(v["ticker"], v.get("market", "TW")),
                    }
                    for v in rows
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)


def price_chart(prices: list[dict]) -> go.Figure:
    df = pd.DataFrame(prices)
    if df.empty:
        return go.Figure()
    df = df.sort_values("trade_date")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df["trade_date"], y=df["close_price"], name="收盤價", line=dict(color="#2563eb")),
        secondary_y=False,
    )
    if df["ma20"].notna().any():
        fig.add_trace(
            go.Scatter(x=df["trade_date"], y=df["ma20"], name="MA20", line=dict(color="#f59e0b", dash="dash")),
            secondary_y=False,
        )
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h"))
    fig.update_yaxes(title_text="股價 (TWD)", secondary_y=False)
    return fig


def yield_chart(yields: list[dict]) -> go.Figure:
    df = pd.DataFrame(yields)
    if df.empty:
        return go.Figure()
    df = df.sort_values("trade_date")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["trade_date"],
            y=df["dividend_yield_pct"],
            name="殖利率 %",
            fill="tozeroy",
            line=dict(color="#16a34a"),
        )
    )
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="殖利率 (%)")
    return fig


def render_market_watch():
    st.subheader("股價與殖利率")
    tickers = unique_watch_tickers()
    ticker = st.selectbox("選擇標的", tickers)

    client = db_client()
    prices = fetch_prices(client, ticker)
    yields = fetch_yields(client, ticker)
    dividends = fetch_dividends(client, ticker)
    eps_rows = fetch_eps(client, ticker)

    if prices:
        latest = prices[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("收盤", f"{latest['close_price']:.2f}")
        c2.metric("最高", f"{latest['high_price']:.2f}")
        c3.metric("最低", f"{latest['low_price']:.2f}")
        c4.metric("MA20", f"{latest['ma20']:.2f}" if latest.get("ma20") else "—")
        if yields:
            c5.metric("殖利率", f"{yields[0]['dividend_yield_pct']:.2f}%")
        else:
            c5.metric("殖利率", "—")

        st.plotly_chart(price_chart(prices), use_container_width=True)
    else:
        st.warning("尚無股價資料，請按「立即更新」。")

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**殖利率走勢**")
        if yields:
            st.plotly_chart(yield_chart(yields), use_container_width=True)
            st.caption(f"近 12 月股利合計：{yields[0].get('trailing_12m_div', 0):.2f} 元")
        else:
            st.info("尚無殖利率資料")

    with col_r:
        st.markdown("**歷史股利**")
        if dividends:
            st.dataframe(
                pd.DataFrame(dividends)[["ex_date", "cash_dividend", "fiscal_year"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("尚無股利資料")

    st.markdown("**歷史 EPS（季度）**")
    if eps_rows:
        st.dataframe(
            pd.DataFrame(eps_rows)[["fiscal_period", "period_end", "eps", "source_type"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("尚無 EPS 資料（部分台股小票 yfinance 可能缺資料）")


def render_overview_table():
    st.subheader("觀察清單總覽")
    client = db_client()
    rows = []
    for ticker in unique_watch_tickers():
        prices = fetch_prices(client, ticker, limit=2)
        yields = fetch_yields(client, ticker, limit=1)
        if not prices:
            rows.append({"標的": ticker, "收盤": None, "漲跌%": None, "MA20": None, "殖利率%": None})
            continue
        latest = prices[0]
        prev_close = float(prices[1]["close_price"]) if len(prices) > 1 else None
        chg = None
        if prev_close and prev_close > 0:
            chg = (float(latest["close_price"]) - prev_close) / prev_close * 100
        rows.append(
            {
                "標的": ticker,
                "收盤": latest["close_price"],
                "漲跌%": round(chg, 2) if chg is not None else None,
                "MA20": latest.get("ma20"),
                "殖利率%": yields[0]["dividend_yield_pct"] if yields else None,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def main():
    render_refresh_bar()
    st.divider()
    tab1, tab2, tab3 = st.tabs(["總覽", "供應鏈", "個股詳情"])
    with tab1:
        render_overview_table()
    with tab2:
        render_supply_chain()
    with tab3:
        render_market_watch()


if __name__ == "__main__":
    main()
