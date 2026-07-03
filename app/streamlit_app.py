import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
ASSETS = ROOT / "assets"

from src.config import load_categories, load_vendors
from src.db import (
    fetch_dividends,
    fetch_eps,
    fetch_prices,
    fetch_yields,
    get_client,
    latest_sync,
)
from src.fundamentals import fetch_extended_fundamentals
from src.symbol_resolver import resolve_yfinance_symbol, unique_resolved_tickers
from src.sync import run_full_sync
from src.valuation import (
    assessment_style,
    fair_value_52w_mid,
    fair_value_by_eps,
    ma_position_label,
    pct_vs,
    price_assessment,
)
from src.vendor_meta import build_ticker_meta, categories_for, company_for
from src.ux_helpers import (
    category_options,
    category_short_name,
    primary_category,
    ticker_select_label,
    tickers_in_category,
)

st.set_page_config(
    page_title="BotChainVision",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLOR_UP = "#ef4444"
COLOR_DOWN = "#22c55e"
COLOR_GOLDEN = "#fbbf24"
COLOR_DEATH = "#a855f7"

CATEGORY_ICONS = {
    "drivetrain": "⚙️",
    "motor": "🔌",
    "pcb": "🖥️",
    "vision": "👁️",
    "structure": "🏗️",
}


@st.cache_resource
def db_client():
    return get_client()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fundamentals(ticker: str, close: float) -> dict:
    return fetch_extended_fundamentals(ticker, close_price=close)


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


def build_overview_rows(client, meta: dict) -> list[dict]:
    rows = []
    for ticker in unique_resolved_tickers():
        prices = fetch_prices(client, ticker, limit=2)
        yields = fetch_yields(client, ticker, limit=1)
        company = company_for(ticker, meta)
        supply_chain = primary_category(ticker, meta)

        if not prices:
            rows.append({"ticker": ticker, "公司名稱": company, "供應鏈環節": supply_chain})
            continue

        latest = prices[0]
        close = float(latest["close_price"])
        prev_close = float(prices[1]["close_price"]) if len(prices) > 1 else None
        chg = (close - prev_close) / prev_close * 100 if prev_close and prev_close > 0 else None
        ma20 = latest.get("ma20")
        ma60 = latest.get("ma60")
        vs_ma20 = pct_vs(close, ma20)
        vs_ma60 = pct_vs(close, ma60)

        fund = cached_fundamentals(ticker, close)
        pe = latest.get("pe_ratio") or fund.get("pe_ratio")
        eps = latest.get("eps_ttm") or fund.get("eps_ttm")
        roe_pct = fund.get("roe_pct")
        fair_eps = fair_value_by_eps(eps)
        fair_52w = fair_value_52w_mid(fund.get("week52_low"), fund.get("week52_high"))
        fair_ref = fair_eps or fair_52w
        assessment = price_assessment(close, pe, vs_ma20, vs_ma60, fair_eps, fund.get("roe"))
        yield_val = yields[0]["dividend_yield_pct"] if yields else None

        rows.append(
            {
                "ticker": ticker,
                "公司名稱": company,
                "供應鏈環節": supply_chain,
                "收盤": close,
                "前一天收盤": prev_close,
                "漲跌%": round(chg, 2) if chg is not None else None,
                "距MA20%": vs_ma20,
                "距MA60%": vs_ma60,
                "均線位置": ma_position_label(vs_ma20, vs_ma60),
                "本益比": round(pe, 2) if pe else None,
                "ROE%": roe_pct,
                "合理價參考": fair_ref,
                "價格評價": assessment,
                "短線狀態": latest.get("signal_short"),
                "中線狀態": latest.get("signal_medium"),
                "殖利率%": round(yield_val, 2) if yield_val is not None else None,
            }
        )
    return rows


def render_sidebar(meta: dict) -> tuple[str | None, str | None]:
    st.sidebar.header("🔍 導覽")
    cats = category_options()
    cat_labels = {"all": "全部環節"}
    for c in cats:
        icon = CATEGORY_ICONS.get(c["id"], "📦")
        cat_labels[c["id"]] = f"{icon} {category_short_name(c['name'])}"

    selected_cat = st.sidebar.selectbox(
        "供應鏈環節",
        options=["all"] + [c["id"] for c in cats],
        format_func=lambda x: cat_labels.get(x, x),
    )

    filtered = tickers_in_category(selected_cat, meta)
    if not filtered:
        filtered = list(meta.keys())

    selected_ticker = st.sidebar.selectbox(
        "選擇公司",
        options=filtered,
        format_func=lambda s: ticker_select_label(s, meta),
    )

    st.sidebar.divider()
    st.sidebar.caption(
        "💡 **價格評價** 綜合本益比、距均線%、EPS合理價參考，"
        "僅供篩選參考，非投資建議。"
    )
    return selected_cat, selected_ticker


def render_refresh_bar():
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        refresh = st.button("🔄 立即更新", type="primary", use_container_width=True)
    with col2:
        backfill = st.selectbox(
            "回補天數",
            [90, 180, 365, 730],
            index=0,
            label_visibility="collapsed",
        )
    with col3:
        try:
            last = latest_sync(db_client())
            if last:
                st.caption(f"上次同步：{last.get('finished_at', '')[:19]}")
        except Exception:
            st.caption("尚未同步")

    if refresh:
        with st.spinner("更新中…"):
            try:
                result = run_full_sync(source="manual", backfill_days=int(backfill))
                st.success(f"已更新 {result['tickers_count']} 檔")
                cached_fundamentals.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"更新失敗：{exc}")


def render_screener(meta: dict, cat_filter: str | None):
    st.subheader("投資總覽｜價值篩選")
    st.caption("依供應鏈環節檢視股價是否偏低、本益比與 ROE 是否合理")

    client = db_client()
    rows = build_overview_rows(client, meta)
    df = pd.DataFrame(rows)

    if cat_filter and cat_filter != "all":
        cat_name = category_short_name(
            next((c["name"] for c in load_categories() if c["id"] == cat_filter), "")
        )
        df = df[df["供應鏈環節"] == cat_name]

    c1, c2, c3 = st.columns(3)
    with c1:
        sort_by = st.selectbox(
            "排序",
            ["價格評價", "距MA20%", "本益比", "ROE%", "殖利率%", "公司名稱"],
            label_visibility="visible",
        )
    with c2:
        show_only = st.multiselect(
            "篩選評價",
            ["偏低", "合理", "偏高"],
            default=["偏低", "合理", "偏高"],
        )
    with c3:
        ma_filter = st.selectbox("均線位置", ["全部", "低於均線", "高於均線", "均線附近"])

    if show_only and "價格評價" in df.columns:
        df = df[df["價格評價"].isin(show_only)]
    if ma_filter != "全部" and "均線位置" in df.columns:
        df = df[df["均線位置"] == ma_filter]

    if sort_by == "價格評價" and "價格評價" in df.columns:
        order = {"偏低": 0, "合理": 1, "偏高": 2, "—": 3}
        df["_sort"] = df["價格評價"].map(order).fillna(9)
        df = df.sort_values("_sort").drop(columns="_sort")
    else:
        asc_cols = {"距MA20%", "本益比"}
        df = df.sort_values(
            by=sort_by if sort_by in df.columns else "公司名稱",
            ascending=sort_by in asc_cols,
            na_position="last",
        )

    display_cols = [
        "公司名稱",
        "供應鏈環節",
        "收盤",
        "漲跌%",
        "距MA20%",
        "距MA60%",
        "均線位置",
        "本益比",
        "ROE%",
        "合理價參考",
        "價格評價",
        "短線狀態",
        "殖利率%",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    view = df[display_cols]

    fmt = {
        "收盤": "{:.2f}",
        "前一天收盤": "{:.2f}",
        "漲跌%": "{:+.2f}",
        "距MA20%": "{:+.2f}",
        "距MA60%": "{:+.2f}",
        "本益比": "{:.2f}",
        "ROE%": "{:.2f}",
        "合理價參考": "{:.2f}",
        "殖利率%": "{:.2f}",
    }
    styled = view.style.format(fmt, na_rep="—")
    styled = styled.map(_chg_style, subset=["漲跌%"])
    styled = styled.map(assessment_style, subset=["價格評價"])
    for col in ["短線狀態", "中線狀態"]:
        if col in view.columns:
            styled = styled.map(_signal_style, subset=[col])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    low_df = df[df["價格評價"] == "偏低"].head(5)
    if not low_df.empty:
        st.markdown("#### 🟢 目前偏低的標的（依評價模型）")
        for _, r in low_df.iterrows():
            st.markdown(
                f"- **{r['公司名稱']}**（{r['供應鏈環節']}）收盤 {r['收盤']:.2f}｜"
                f"距MA20 {r.get('距MA20%', '—')}%｜本益比 {r.get('本益比', '—')}｜"
                f"合理價參考 {r.get('合理價參考', '—')}"
            )


def render_stock_detail(ticker: str, meta: dict):
    company = company_for(ticker, meta)
    category = categories_for(ticker, meta)
    cat_short = primary_category(ticker, meta)

    st.subheader(f"{company}")
    badges = f"`{meta.get(ticker, {}).get('ticker_code', '')}` · {ticker} · 📂 {cat_short}"
    st.caption(badges)
    if "、" in category:
        st.info(f"供應鏈角色：{category}")

    client = db_client()
    prices = fetch_prices(client, ticker)
    yields = fetch_yields(client, ticker)
    dividends = fetch_dividends(client, ticker)
    eps_rows = fetch_eps(client, ticker)

    if not prices:
        st.warning("尚無股價資料，請按「立即更新」。")
        return

    latest = prices[0]
    close = float(latest["close_price"])
    fund = cached_fundamentals(ticker, close)
    ma20, ma60 = latest.get("ma20"), latest.get("ma60")
    vs_ma20, vs_ma60 = pct_vs(close, ma20), pct_vs(close, ma60)
    pe = latest.get("pe_ratio") or fund.get("pe_ratio")
    eps = latest.get("eps_ttm") or fund.get("eps_ttm")
    fair_eps = fair_value_by_eps(eps)
    fair_52w = fair_value_52w_mid(fund.get("week52_low"), fund.get("week52_high"))
    assessment = price_assessment(close, pe, vs_ma20, vs_ma60, fair_eps, fund.get("roe"))

    st.markdown("#### 💰 價值判斷")
    v1, v2, v3, v4, v5 = st.columns(5)
    v1.metric("價格評價", assessment)
    v2.metric("距 MA20", f"{vs_ma20:+.1f}%" if vs_ma20 is not None else "—")
    v3.metric("距 MA60", f"{vs_ma60:+.1f}%" if vs_ma60 is not None else "—")
    v4.metric("合理價(EPS×15)", f"{fair_eps:.2f}" if fair_eps else "—")
    v5.metric("52週中位參考", f"{fair_52w:.2f}" if fair_52w else "—")

    st.caption(
        f"均線位置：**{ma_position_label(vs_ma20, vs_ma60)}**｜"
        f"ROE：**{fund.get('roe_pct') or '—'}%**｜"
        f"52週：**{fund.get('week52_low') or '—'} ~ {fund.get('week52_high') or '—'}**"
    )

    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    c1.metric("收盤", f"{close:.2f}")
    c2.metric("MA5", f"{latest['ma5']:.2f}" if latest.get("ma5") else "—")
    c3.metric("MA20", f"{ma20:.2f}" if ma20 else "—")
    c4.metric("MA60", f"{ma60:.2f}" if ma60 else "—")
    c5.metric("本益比", f"{pe:.2f}" if pe else "—")
    c6.metric("ROE", f"{fund.get('roe_pct') or '—'}%")
    if yields:
        c7.metric("殖利率", f"{yields[0]['dividend_yield_pct']:.2f}%")
    else:
        c7.metric("殖利率", "—")
    c8.metric("短線", latest.get("signal_short") or "—")

    fig = price_chart(prices, fair_eps=fair_eps, fair_52w=fair_52w)
    st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**殖利率走勢**")
        if yields:
            st.plotly_chart(yield_chart(yields), use_container_width=True)
    with col_r:
        st.markdown("**歷史股利**")
        if dividends:
            st.dataframe(pd.DataFrame(dividends)[["ex_date", "cash_dividend"]], hide_index=True)

    if eps_rows:
        st.markdown("**歷史 EPS**")
        st.dataframe(pd.DataFrame(eps_rows)[["fiscal_period", "eps"]], hide_index=True)


def price_chart(prices: list[dict], fair_eps: float | None = None, fair_52w: float | None = None) -> go.Figure:
    df = pd.DataFrame(prices).sort_values("trade_date")
    fig = make_subplots()
    fig.add_trace(go.Scatter(x=df["trade_date"], y=df["close_price"], name="收盤", line=dict(color="#2563eb")))
    for col, label, color, dash in [
        ("ma5", "MA5", "#22c55e", "dot"),
        ("ma20", "MA20", "#f59e0b", "dash"),
        ("ma60", "MA60", "#a855f7", "dashdot"),
    ]:
        if col in df.columns and df[col].notna().any():
            fig.add_trace(go.Scatter(x=df["trade_date"], y=df[col], name=label, line=dict(color=color, dash=dash)))
    for val, name, color in [
        (fair_eps, "合理價(EPS×15)", "#22c55e"),
        (fair_52w, "52週中位", "#94a3b8"),
    ]:
        if val:
            fig.add_hline(y=val, line_dash="dot", line_color=color, annotation_text=name)
    fig.update_layout(height=460, legend=dict(orientation="h"), margin=dict(l=20, r=20, t=30, b=20))
    return fig


def yield_chart(yields: list[dict]) -> go.Figure:
    df = pd.DataFrame(yields).sort_values("trade_date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["trade_date"], y=df["dividend_yield_pct"], fill="tozeroy"))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=20))
    return fig


def render_component_map():
    st.subheader("人形機器人元件分布")
    robot_img = ASSETS / "robot_components.png"
    if robot_img.exists():
        st.image(str(robot_img), use_container_width=True)
    cat_map = {c["id"]: c for c in load_categories()}
    rows = []
    for v in load_vendors():
        cat = cat_map.get(v["category_id"], {})
        rows.append(
            {
                "環節": category_short_name(cat.get("name", "")),
                "元件範例": cat.get("component_examples", ""),
                "公司": v["company"],
                "代號": v["ticker"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_supply_chain():
    st.subheader("供應鏈地圖")
    meta = build_ticker_meta()
    for cat in load_categories():
        icon = CATEGORY_ICONS.get(cat["id"], "📦")
        with st.expander(f"{icon} {cat['name']}", expanded=False):
            st.markdown(f"**元件：** {cat['component_examples']}")
            rows = [
                {
                    "公司": company_for(resolve_yfinance_symbol(v["ticker"], v.get("market", "TW")), meta),
                    "代號": v["ticker"],
                }
                for v in load_vendors()
                if v["category_id"] == cat["id"]
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_about():
    st.markdown(
        """
        ### 如何使用這個 Dashboard

        1. **左側欄**：先選「供應鏈環節」，再選「公司」（會顯示公司名＋代號＋環節）
        2. **投資總覽**：一次比較所有標的的價格評價、距均線%、本益比、ROE
        3. **個股深度**：看合理價參考線、52週區間、均線狀態

        ### 指標說明

        | 指標 | 意義 |
        |------|------|
        | **距MA20% / 距MA60%** | 收盤價偏離均線；負值=在均線下方 |
        | **合理價(EPS×15)** | EPS × 15 的簡易參考（可調整） |
        | **52週中位** | 過去52週高低點的中間值 |
        | **ROE%** | 股東權益報酬率，越高通常代表體質越好 |
        | **價格評價** | 綜合本益比、均線、合理價的啟發式標籤（非投資建議） |
        | **黃金/死亡交叉** | 短均線穿越長均線的技術訊號 |

        ### 為什麼要 ROE + 本益比？

        - **本益比**告訴你「賺多少錢對應多少股價」
        - **ROE**告訴你「公司用股東資金賺錢的效率」
        - 搭配 **距均線%** 可看短期是否超跌/超漲
        - **合理價參考**幫助判斷「大概什麼價位算便宜」
        """
    )


def main():
    meta = build_ticker_meta()
    cat_filter, selected_ticker = render_sidebar(meta)

    st.title("🤖 BotChainVision")
    st.caption("人形機器人供應鏈 × 台股投資儀表板")
    render_refresh_bar()
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 投資總覽", "🤖 元件分布", "🔗 供應鏈", "📈 個股深度", "❓ 說明"]
    )
    with tab1:
        render_screener(meta, cat_filter)
    with tab2:
        render_component_map()
    with tab3:
        render_supply_chain()
    with tab4:
        if selected_ticker:
            render_stock_detail(selected_ticker, meta)
        else:
            st.info("請從左側欄選擇供應鏈環節與公司")
    with tab5:
        render_about()


if __name__ == "__main__":
    main()
