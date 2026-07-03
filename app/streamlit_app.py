import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
ASSETS = ROOT / "assets"

from src.config import load_categories, load_vendors, to_yfinance_symbol
from src.symbol_resolver import resolve_yfinance_symbol, unique_resolved_tickers
from src.db import (
    fetch_dividends,
    fetch_eps,
    fetch_prices,
    fetch_yields,
    get_client,
    latest_sync,
)
from src.sync import run_full_sync
from src.vendor_meta import build_ticker_meta, categories_for, company_for

st.set_page_config(
    page_title="BotChainVision",
    page_icon="🤖",
    layout="wide",
)

# Taiwan market: 漲紅跌綠
COLOR_UP = "#ef4444"
COLOR_DOWN = "#22c55e"
COLOR_GOLDEN = "#fbbf24"
COLOR_DEATH = "#a855f7"


@st.cache_resource
def db_client():
    return get_client()


def _signal_style(val: str | None) -> str:
    if not val:
        return ""
    if val == "黃金交叉":
        return f"color: {COLOR_GOLDEN}; font-weight: bold"
    if val == "死亡交叉":
        return f"color: {COLOR_DEATH}; font-weight: bold"
    if val == "多頭":
        return f"color: {COLOR_UP}"
    if val == "空頭":
        return f"color: {COLOR_DOWN}"
    return ""


def _chg_style(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if val > 0:
        return f"color: {COLOR_UP}; font-weight: bold"
    if val < 0:
        return f"color: {COLOR_DOWN}; font-weight: bold"
    return ""


def render_refresh_bar():
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        refresh = st.button("🔄 立即更新股價與殖利率", type="primary", use_container_width=True)
    with col2:
        backfill = st.selectbox(
            "回補天數",
            [90, 180, 365, 730],
            index=0,
            label_visibility="collapsed",
            help="首次建議 730（2年）；日常更新選 90 即可，舊資料會保留累積",
        )
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
                st.success(f"已更新 {result['tickers_count']} 檔標的（{result['price_rows']} 筆股價）")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"更新失敗：{exc}")
                st.info("請確認已在 Supabase 執行 migration 002，且 .env / Secrets 設定正確。")


def render_component_map():
    st.subheader("人形機器人元件分布")
    robot_img = ASSETS / "robot_components.png"
    if robot_img.exists():
        st.image(str(robot_img), use_container_width=True, caption="人形機器人關鍵零組件示意圖")
    else:
        st.info("將元件示意圖放至 `assets/robot_components.png` 即可顯示。下方為供應鏈對照表。")

    st.markdown("#### 關鍵技術 × 元件 × 台股供應鏈")
    cat_map = {c["id"]: c for c in load_categories()}
    rows = []
    for v in load_vendors():
        cat = cat_map.get(v["category_id"], {})
        rows.append(
            {
                "關鍵技術/製程": cat.get("name", ""),
                "對應元件範例": cat.get("component_examples", ""),
                "公司": v["company"],
                "代號": v["ticker"],
                "市場": v.get("market", "TW"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
                        "YFinance": resolve_yfinance_symbol(v["ticker"], v.get("market", "TW")),
                    }
                    for v in rows
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)


def price_chart(prices: list[dict]) -> go.Figure:
    df = pd.DataFrame(prices).sort_values("trade_date")
    if df.empty:
        return go.Figure()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df["trade_date"], y=df["close_price"], name="收盤價", line=dict(color="#2563eb")),
        secondary_y=False,
    )
    ma_specs = [
        ("ma5", "MA5", "#22c55e", "dot"),
        ("ma20", "MA20", "#f59e0b", "dash"),
        ("ma60", "MA60", "#a855f7", "dashdot"),
    ]
    for col, label, color, dash in ma_specs:
        if col in df.columns and df[col].notna().any():
            fig.add_trace(
                go.Scatter(x=df["trade_date"], y=df[col], name=label, line=dict(color=color, dash=dash)),
                secondary_y=False,
            )
    fig.update_layout(height=440, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h"))
    fig.update_yaxes(title_text="股價 (TWD)", secondary_y=False)
    return fig


def yield_chart(yields: list[dict]) -> go.Figure:
    df = pd.DataFrame(yields).sort_values("trade_date")
    if df.empty:
        return go.Figure()
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
    meta = build_ticker_meta()
    tickers = unique_resolved_tickers()
    ticker = st.selectbox(
        "選擇標的",
        tickers,
        format_func=lambda s: f"{company_for(s, meta)} ({s})",
    )

    company = company_for(ticker, meta)
    category = categories_for(ticker, meta)
    st.markdown(f"### {company} `{ticker}`")
    st.caption(f"📂 {category}")

    client = db_client()
    prices = fetch_prices(client, ticker)
    yields = fetch_yields(client, ticker)
    dividends = fetch_dividends(client, ticker)
    eps_rows = fetch_eps(client, ticker)

    if prices:
        latest = prices[0]
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        c1.metric("收盤", f"{latest['close_price']:.2f}")
        c2.metric("最高", f"{latest['high_price']:.2f}")
        c3.metric("最低", f"{latest['low_price']:.2f}")
        c4.metric("MA5", f"{latest['ma5']:.2f}" if latest.get("ma5") else "—")
        c5.metric("MA20", f"{latest['ma20']:.2f}" if latest.get("ma20") else "—")
        c6.metric("MA60", f"{latest['ma60']:.2f}" if latest.get("ma60") else "—")
        pe = latest.get("pe_ratio")
        c7.metric("本益比", f"{pe:.2f}" if pe else "—")
        if yields:
            c8.metric("殖利率", f"{yields[0]['dividend_yield_pct']:.2f}%")
        else:
            c8.metric("殖利率", "—")

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f"**短線狀態 (MA5×MA20)：** {latest.get('signal_short') or '—'}")
        with sc2:
            st.markdown(f"**中線狀態 (MA20×MA60)：** {latest.get('signal_medium') or '—'}")

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
    meta = build_ticker_meta()
    client = db_client()
    rows = []

    for ticker in unique_resolved_tickers():
        prices = fetch_prices(client, ticker, limit=2)
        yields = fetch_yields(client, ticker, limit=1)
        company = company_for(ticker, meta)

        if not prices:
            rows.append(
                {
                    "公司名稱": company,
                    "標的": ticker,
                    "收盤": None,
                    "前一天收盤": None,
                    "漲跌%": None,
                    "短線狀態": None,
                    "中線狀態": None,
                    "本益比": None,
                    "殖利率%": None,
                }
            )
            continue

        latest = prices[0]
        prev_close = float(prices[1]["close_price"]) if len(prices) > 1 else None
        chg = None
        if prev_close and prev_close > 0:
            chg = (float(latest["close_price"]) - prev_close) / prev_close * 100

        yield_val = yields[0]["dividend_yield_pct"] if yields else None
        rows.append(
            {
                "公司名稱": company,
                "標的": ticker,
                "收盤": latest["close_price"],
                "前一天收盤": prev_close,
                "漲跌%": round(chg, 2) if chg is not None else None,
                "短線狀態": latest.get("signal_short"),
                "中線狀態": latest.get("signal_medium"),
                "本益比": round(latest["pe_ratio"], 2) if latest.get("pe_ratio") else None,
                "殖利率%": round(yield_val, 2) if yield_val is not None else None,
            }
        )

    df = pd.DataFrame(rows)

    fmt = {
        "收盤": "{:.2f}",
        "前一天收盤": "{:.2f}",
        "漲跌%": "{:+.2f}",
        "本益比": "{:.2f}",
        "殖利率%": "{:.2f}",
    }
    styled = df.style.format(fmt, na_rep="—")
    if "漲跌%" in df.columns:
        styled = styled.map(_chg_style, subset=["漲跌%"])
    for col in ["短線狀態", "中線狀態"]:
        if col in df.columns:
            styled = styled.map(_signal_style, subset=[col])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.caption(
        "短線：MA5×MA20｜中線：MA20×MA60｜"
        "黃金交叉=買進訊號｜死亡交叉=賣出/觀望｜多頭/空頭=當前排列（非當日交叉）"
    )


def main():
    st.title("🤖 BotChainVision")
    st.caption("人形機器人關鍵零組件 × 台股供應鏈追蹤")

    render_refresh_bar()
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["總覽", "元件分布", "供應鏈", "個股詳情", "關於"]
    )
    with tab1:
        render_overview_table()
    with tab2:
        render_component_map()
    with tab3:
        render_supply_chain()
    with tab4:
        render_market_watch()
    with tab5:
        st.markdown(
            """
            **均線狀態說明**
            - **黃金交叉**：短均線由下往上穿越長均線（買進訊號）
            - **死亡交叉**：短均線由上往下穿越長均線（賣出/觀望訊號）
            - **多頭 / 空頭**：當前排列狀態，當日未發生交叉

            **資料累積**：每日同步會保留歷史股價；首次建議回補 730 天。
            """
        )


if __name__ == "__main__":
    main()
