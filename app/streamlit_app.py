import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

# Import before adding project root — ./supabase/ migrations must not shadow the PyPI package.
from supabase import Client, create_client  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(ROOT))
ASSETS = ROOT / "assets"

from eps_chart import (
    build_five_year_rows,
    expected_dividend_yield_pct,
    last_payout_ratio,
    summary_caption,
    trailing_four_quarters_eps,
)

from src.category_pe import fair_pe_label, reference_pe_for_category, reference_pe_map
from src.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, load_categories
from src.db import (
    fetch_dividends,
    fetch_eps,
    fetch_prices,
    fetch_yields,
    get_client,
    latest_sync,
)
from src.fundamentals import fetch_extended_fundamentals
from src.symbol_resolver import unique_resolved_tickers
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
    format_tw_datetime,
    primary_category,
    primary_category_id,
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
    "com_som": "💻",
    "vision": "👁️",
    "structure": "🏗️",
}


def _check_config() -> bool:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        st.error(
            "缺少 Supabase 設定。本機請建立 `.env`；雲端請在 Streamlit Cloud → Secrets 設定 "
            "`SUPABASE_URL` 與 `SUPABASE_SERVICE_ROLE_KEY`。"
        )
        st.code(
            "SUPABASE_URL = \"https://verzhajfabdmnkmedjfo.supabase.co\"\n"
            "SUPABASE_SERVICE_ROLE_KEY = \"your_key\"",
            language="toml",
        )
        return False
    return True


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
    cat_map = {c["id"]: c for c in load_categories()}
    rows = []
    for ticker in unique_resolved_tickers():
        prices = fetch_prices(client, ticker, limit=2)
        yields = fetch_yields(client, ticker, limit=1)
        company = company_for(ticker, meta)
        supply_chain = primary_category(ticker, meta)
        cat_id = primary_category_id(ticker, meta)
        ref_pe = reference_pe_for_category(cat_id)
        ticker_code = meta.get(ticker, {}).get("ticker_code", "")
        component_examples = cat_map.get(cat_id or "", {}).get("component_examples", "")

        if not prices:
            rows.append(
                {
                    "ticker": ticker,
                    "公司名稱": company,
                    "代號": ticker_code,
                    "供應鏈環節": supply_chain,
                    "元件範例": component_examples,
                    "參考PE": ref_pe,
                }
            )
            continue

        latest = prices[0]
        close = float(latest["close_price"])
        prev_close = float(prices[1]["close_price"]) if len(prices) > 1 else None
        chg = (close - prev_close) / prev_close * 100 if prev_close and prev_close > 0 else None
        ma20, ma60 = latest.get("ma20"), latest.get("ma60")
        vs_ma20, vs_ma60 = pct_vs(close, ma20), pct_vs(close, ma60)

        fund = cached_fundamentals(ticker, close)
        pe = latest.get("pe_ratio") or fund.get("pe_ratio")
        eps = latest.get("eps_ttm") or fund.get("eps_ttm")
        fair_eps = fair_value_by_eps(eps, ref_pe)
        fair_52w = fair_value_52w_mid(fund.get("week52_low"), fund.get("week52_high"))
        fair_ref = fair_eps or fair_52w
        assessment = price_assessment(
            close, pe, vs_ma20, vs_ma60, fair_eps, fund.get("roe"), reference_pe=ref_pe
        )
        yield_val = yields[0]["dividend_yield_pct"] if yields else None

        rows.append(
            {
                "ticker": ticker,
                "公司名稱": company,
                "代號": ticker_code,
                "供應鏈環節": supply_chain,
                "元件範例": component_examples,
                "收盤": close,
                "前一天收盤": prev_close,
                "漲跌%": round(chg, 2) if chg is not None else None,
                "距MA20%": vs_ma20,
                "距MA60%": vs_ma60,
                "均線位置": ma_position_label(vs_ma20, vs_ma60),
                "本益比": round(pe, 2) if pe else None,
                "參考PE": ref_pe,
                "ROE%": fund.get("roe_pct"),
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
        pe = reference_pe_for_category(c["id"])
        cat_labels[c["id"]] = f"{icon} {category_short_name(c['name'])} (PE{pe:g})"

    selected_cat = st.sidebar.selectbox(
        "供應鏈環節",
        options=["all"] + [c["id"] for c in cats],
        format_func=lambda x: cat_labels.get(x, x),
    )

    filtered = tickers_in_category(selected_cat, meta) or list(meta.keys())
    if "selected_ticker" not in st.session_state or st.session_state.selected_ticker not in filtered:
        st.session_state.selected_ticker = filtered[0] if filtered else None

    default_idx = (
        filtered.index(st.session_state.selected_ticker)
        if st.session_state.selected_ticker in filtered
        else 0
    )
    selected_ticker = st.sidebar.selectbox(
        "選擇公司",
        options=filtered,
        index=default_idx,
        format_func=lambda s: ticker_select_label(s, meta),
    )
    st.session_state.selected_ticker = selected_ticker

    st.sidebar.divider()
    st.sidebar.caption("合理價 = EPS × 該環節參考本益比（見「說明」分頁）")
    return selected_cat, selected_ticker


def render_refresh_bar():
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        refresh = st.button("🔄 立即更新", type="primary", use_container_width=True)
    with col2:
        backfill = st.selectbox("回補天數", [90, 180, 365, 730], index=0, label_visibility="collapsed")
    with col3:
        try:
            last = latest_sync(db_client())
            if last:
                st.caption(f"上次同步：{format_tw_datetime(last.get('finished_at'))}（台灣時間）")
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


def render_supply_chain_overview(meta: dict, cat_filter: str | None):
    st.subheader("供應鏈總覽")
    st.caption("點選表格中的公司列，將自動跳至「個股深度」｜合理價依供應鏈環節使用不同參考本益比")

    try:
        client = db_client()
        rows = build_overview_rows(client, meta)
    except Exception as exc:
        st.error(f"無法讀取資料：{exc}")
        return

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("尚無資料，請按「立即更新」。")
        return

    if cat_filter and cat_filter != "all":
        cat_name = category_short_name(
            next((c["name"] for c in load_categories() if c["id"] == cat_filter), "")
        )
        df = df[df["供應鏈環節"] == cat_name]

    c1, c2, c3 = st.columns(3)
    with c1:
        sort_by = st.selectbox("排序", ["供應鏈環節", "價格評價", "距MA20%", "本益比", "ROE%", "殖利率%", "公司名稱"])
    with c2:
        show_only = st.multiselect("篩選評價", ["偏低", "合理", "偏高"], default=["偏低", "合理", "偏高"])
    with c3:
        ma_filter = st.selectbox("均線位置", ["全部", "低於均線", "高於均線", "均線附近"])

    if show_only and "價格評價" in df.columns:
        df = df[df["價格評價"].isin(show_only)]
    if ma_filter != "全部" and "均線位置" in df.columns:
        df = df[df["均線位置"] == ma_filter]

    if sort_by == "價格評價" and "價格評價" in df.columns:
        order = {"偏低": 0, "合理": 1, "偏高": 2, "—": 3}
        df["_sort"] = df["價格評價"].map(order).fillna(9)
        df = df.sort_values(["_sort", "供應鏈環節", "公司名稱"]).drop(columns="_sort")
    elif sort_by == "供應鏈環節":
        df = df.sort_values(["供應鏈環節", "公司名稱"], na_position="last")
    else:
        df = df.sort_values(
            by=sort_by if sort_by in df.columns else "公司名稱",
            ascending=sort_by in {"距MA20%", "本益比"},
            na_position="last",
        )

    display_cols = [
        "公司名稱", "代號", "供應鏈環節", "元件範例",
        "收盤", "漲跌%", "距MA20%", "距MA60%", "均線位置",
        "本益比", "參考PE", "ROE%", "合理價參考", "價格評價", "短線狀態", "殖利率%",
    ]
    view = df[[c for c in display_cols if c in df.columns]].reset_index(drop=True)

    fmt = {
        "收盤": "{:.2f}", "漲跌%": "{:+.2f}", "距MA20%": "{:+.2f}", "距MA60%": "{:+.2f}",
        "本益比": "{:.2f}", "參考PE": "{:.0f}", "ROE%": "{:.2f}",
        "合理價參考": "{:.2f}", "殖利率%": "{:.2f}",
    }
    styled = view.style.format(fmt, na_rep="—")
    styled = styled.map(_chg_style, subset=["漲跌%"])
    styled = styled.map(assessment_style, subset=["價格評價"])
    if "短線狀態" in view.columns:
        styled = styled.map(_signal_style, subset=["短線狀態"])

    selection = st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="supply_chain_overview_df",
    )

    if selection.selection.rows:
        row_idx = selection.selection.rows[0]
        picked = df.iloc[row_idx]["ticker"]
        if st.session_state.get("selected_ticker") != picked:
            st.session_state.selected_ticker = picked
            st.session_state.page = "📈 個股深度"
            st.rerun()

    low_df = df[df["價格評價"] == "偏低"].head(5)
    if not low_df.empty:
        st.markdown("#### 🟢 目前偏低的標的")
        for _, r in low_df.iterrows():
            st.markdown(
                f"- **{r['公司名稱']}**（{r['供應鏈環節']}｜參考PE {r.get('參考PE', '—')}）"
                f" 收盤 {r['收盤']:.2f}｜合理價 {r.get('合理價參考', '—')}"
            )


def render_stock_detail(ticker: str, meta: dict):
    company = company_for(ticker, meta)
    category = categories_for(ticker, meta)
    cat_short = primary_category(ticker, meta)
    cat_id = primary_category_id(ticker, meta)
    ref_pe = reference_pe_for_category(cat_id)
    pe_label = fair_pe_label(cat_id)
    key_tag = ticker
    ticker_code = meta.get(ticker, {}).get("ticker_code", "")

    if ticker_code:
        st.markdown(f"[🔗 Winvest 個股討論](https://winvest.tw/Stock/Symbol/Comment/{ticker_code})")

    st.subheader(company)
    st.caption(f"`{meta.get(ticker, {}).get('ticker_code', '')}` · {ticker} · 📂 {cat_short} · 參考PE **{ref_pe:g}**")
    if "、" in category:
        st.info(f"供應鏈角色：{category}")

    try:
        client = db_client()
        prices = fetch_prices(client, ticker)
        yields = fetch_yields(client, ticker)
        dividends = fetch_dividends(client, ticker)
        eps_rows = fetch_eps(client, ticker)
    except Exception as exc:
        st.error(f"無法讀取資料：{exc}")
        return

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
    fair_eps = fair_value_by_eps(eps, ref_pe)
    fair_52w = fair_value_52w_mid(fund.get("week52_low"), fund.get("week52_high"))
    assessment = price_assessment(
        close, pe, vs_ma20, vs_ma60, fair_eps, fund.get("roe"), reference_pe=ref_pe
    )

    fy_rows = build_five_year_rows(eps_rows, dividends)
    ttm = trailing_four_quarters_eps(eps_rows)
    ttm_eps = ttm.get("ttm_eps")
    payout_ref = last_payout_ratio(fy_rows) if fy_rows else None
    expected_yield = expected_dividend_yield_pct(ttm_eps, close, payout_ref)

    v1, v2, v3, v4, v5 = st.columns(5)
    v1.metric("價格評價", assessment)
    v2.metric("距 MA20", f"{vs_ma20:+.1f}%" if vs_ma20 is not None else "—")
    v3.metric("距 MA60", f"{vs_ma60:+.1f}%" if vs_ma60 is not None else "—")
    v4.metric(f"合理價({pe_label})", f"{fair_eps:.2f}" if fair_eps else "—")
    v5.metric("52週中位", f"{fair_52w:.2f}" if fair_52w else "—")

    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(10)
    c1.metric("收盤", f"{close:.2f}")
    c2.metric("MA5", f"{latest['ma5']:.2f}" if latest.get("ma5") else "—")
    c3.metric("MA20", f"{ma20:.2f}" if ma20 else "—")
    c4.metric("MA60", f"{ma60:.2f}" if ma60 else "—")
    c5.metric("本益比", f"{pe:.2f}" if pe else "—")
    c6.metric("ROE", f"{fund.get('roe_pct') or '—'}%")
    c7.metric("近四季EPS", f"{ttm_eps:.2f}" if ttm_eps is not None else "—")
    c8.metric(
        "預計殖利率",
        f"{expected_yield:.2f}%" if expected_yield is not None else "—",
        help=(
            f"近四季 EPS 加總 × 去年配息率 {payout_ref:.1f}% ÷ 收盤價"
            if expected_yield is not None and payout_ref
            else "需有近四季 EPS 與歷史配息率"
        ),
    )
    c9.metric("殖利率", f"{yields[0]['dividend_yield_pct']:.2f}%" if yields else "—", help="近12月實際股利 ÷ 收盤價")
    c10.metric("短線", latest.get("signal_short") or "—")

    if ttm_eps is not None and ttm.get("periods"):
        suffix = "" if ttm.get("complete") else "（不足四季，加總現有季度）"
        st.caption(f"近四季 EPS = {ttm['periods']}{suffix}")

    st.plotly_chart(
        price_chart(prices, fair_eps=fair_eps, fair_52w=fair_52w, fair_label=pe_label),
        use_container_width=True,
        key=f"price_chart_{key_tag}",
    )

    if fy_rows:
        st.markdown("#### 近五年 EPS × 現金股利")
        st.caption(summary_caption(fy_rows))
        st.plotly_chart(
            eps_dividend_plot(fy_rows),
            use_container_width=True,
            key=f"eps_div_chart_{key_tag}",
        )
        summary_df = pd.DataFrame(
            [
                {
                    "年度": r["year"],
                    "EPS": r["eps_label"] or (f"{r['eps']:.2f}" if r["eps"] is not None else "—"),
                    "現金股利": f"{r['dividend']:.2f}" if r["dividend"] is not None else "—",
                    "配息率%": f"{r['payout_pct']:.1f}" if r["payout_pct"] is not None else "—",
                }
                for r in fy_rows
            ]
        )
        st.dataframe(summary_df, hide_index=True, use_container_width=True, key=f"eps_div_summary_{key_tag}")

    with st.expander("原始股利 / EPS 資料"):
        if ttm_eps is not None:
            st.markdown(
                f"**近四季 EPS 加總：{ttm_eps:.2f}**"
                + (f"（{ttm['periods']}）" if ttm.get("periods") else "")
            )
            if expected_yield is not None and payout_ref is not None:
                expected_div = ttm_eps * payout_ref / 100
                st.caption(
                    f"預計殖利率 = 近四季EPS {ttm_eps:.2f} × 配息率 {payout_ref:.1f}%"
                    f" = 預計股利 {expected_div:.2f} ÷ 收盤 {close:.2f}"
                )
        raw_l, raw_r = st.columns(2)
        with raw_l:
            st.markdown("**現金股利**")
            if dividends:
                st.dataframe(
                    pd.DataFrame(dividends)[["ex_date", "cash_dividend"]],
                    hide_index=True,
                    key=f"dividends_{key_tag}",
                )
            else:
                st.caption("尚無股利資料")
        with raw_r:
            st.markdown("**季度 EPS**")
            if eps_rows:
                eps_df = pd.DataFrame(eps_rows)[["fiscal_period", "period_end", "eps"]]
                st.dataframe(eps_df, hide_index=True, key=f"eps_{key_tag}")
                if ttm.get("quarters"):
                    st.markdown("**近四季明細**")
                    st.dataframe(
                        pd.DataFrame(ttm["quarters"])[["fiscal_period", "period_end", "eps"]],
                        hide_index=True,
                        key=f"eps_ttm_{key_tag}",
                    )
            else:
                st.caption("尚無 EPS 資料")


def eps_dividend_plot(rows: list[dict]) -> go.Figure:
    years = [str(r["year"]) for r in rows]
    eps_vals = [r["eps"] for r in rows]
    div_vals = [r["dividend"] for r in rows]
    payout_vals = [r["payout_pct"] for r in rows]
    eps_text = [
        (r["eps_label"] or "") if r.get("is_ytd") else ""
        for r in rows
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            name="EPS",
            x=years,
            y=eps_vals,
            marker_color="#2563eb",
            text=eps_text,
            textposition="outside",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            name="現金股利",
            x=years,
            y=div_vals,
            marker_color="#f59e0b",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            name="配息率%",
            x=years,
            y=payout_vals,
            mode="lines+markers",
            line=dict(color="#22c55e", width=2),
            marker=dict(size=7),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        height=360,
        barmode="group",
        legend=dict(orientation="h"),
        margin=dict(l=20, r=20, t=30, b=20),
    )
    fig.update_yaxes(title_text="元", secondary_y=False)
    fig.update_yaxes(title_text="配息率 %", secondary_y=True)
    return fig


def price_chart(
    prices: list[dict],
    fair_eps: float | None = None,
    fair_52w: float | None = None,
    fair_label: str = "EPS×PE",
) -> go.Figure:
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
        (fair_eps, f"合理價({fair_label})", "#22c55e"),
        (fair_52w, "52週中位", "#94a3b8"),
    ]:
        if val:
            fig.add_hline(y=val, line_dash="dot", line_color=color, annotation_text=name)
    fig.update_layout(height=460, legend=dict(orientation="h"), margin=dict(l=20, r=20, t=30, b=20))
    return fig


def render_component_map():
    st.subheader("人形機器人元件分布")
    if (ASSETS / "robot_components.png").exists():
        st.image(str(ASSETS / "robot_components.png"), use_container_width=True)
    st.caption("完整供應鏈與股價指標請至「供應鏈總覽」分頁查看。")


def render_about():
    st.markdown("### 供應鏈參考本益比（合理價計算用）")
    pe_rows = [
        {"供應鏈環節": category_short_name(c["name"]), "參考 PE": c.get("reference_pe", 18), "說明": c["component_examples"]}
        for c in load_categories()
    ]
    st.dataframe(pd.DataFrame(pe_rows), hide_index=True)
    st.caption("合理價 = EPS × 參考 PE｜可在 `settings/supply_chain_categories.json` 調整")
    st.markdown(
        """
        ### 指標說明
        - **距MA20% / 距MA60%**：負值代表在均線下方
        - **價格評價**：綜合本益比（對比參考PE）、均線偏離、合理價（非投資建議）
        - **ROE%**：股東權益報酬率
        """
    )


def _suppress_clear_cache_hotkey():
    """Avoid Streamlit 'C' clear-cache dialog when copying text (Ctrl/Cmd+C)."""
    components.html(
        """
        <script>
        (function () {
          const doc = window.parent.document;
          if (doc._bcvHotkeyGuard) return;
          doc._bcvHotkeyGuard = true;
          doc.addEventListener('keydown', function (e) {
            if (e.key !== 'c' && e.key !== 'C') return;
            if (e.ctrlKey || e.metaKey) {
              e.stopImmediatePropagation();
              return;
            }
            const sel = doc.getSelection && doc.getSelection();
            if (sel && sel.toString().length > 0) {
              e.stopImmediatePropagation();
            }
          }, true);
        })();
        </script>
        """,
        height=0,
    )


def main():
    if not _check_config():
        return

    _suppress_clear_cache_hotkey()
    pages = ["📊 供應鏈總覽", "🤖 元件分布", "📈 個股深度", "❓ 說明"]
    if "page" not in st.session_state:
        st.session_state.page = pages[0]

    meta = build_ticker_meta()
    cat_filter, selected_ticker = render_sidebar(meta)

    st.title("🤖 BotChainVision")
    st.caption("人形機器人供應鏈 × 台股投資儀表板")
    render_refresh_bar()
    st.divider()

    page = st.radio(
        "頁面",
        pages,
        index=pages.index(st.session_state.page) if st.session_state.page in pages else 0,
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.page = page

    if page == pages[0]:
        render_supply_chain_overview(meta, cat_filter)
    elif page == pages[1]:
        render_component_map()
    elif page == pages[2]:
        if selected_ticker:
            render_stock_detail(selected_ticker, meta)
        else:
            st.info("請從「供應鏈總覽」表格點選公司列")
    else:
        render_about()


if __name__ == "__main__":
    main()
