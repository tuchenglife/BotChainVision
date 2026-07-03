# BotChainVision TODO

> 待辦事項追蹤 — 與 [requirement.md](requirement.md) 需求 ID 對應

---

## 進行中 🔄

| ID | 項目 | 對應需求 | 備註 |
|----|------|----------|------|
| T-01 | Streamlit Cloud 首次部署 | P-04 | 需於 share.streamlit.io 連結 GitHub repo |

---

## 待辦 ⏳

| ID | 項目 | 對應需求 | 優先級 |
|----|------|----------|--------|
| T-02 | 新聞 RSS 聚合（Google News） | F-09, D-02 | 高 |
| T-03 | 從新聞抽取預估 EPS / 預估營收 | F-09, S-05 | 高 |
| T-04 | 新聞牆 UI 分頁 | F-10 | 中 |
| T-05 | yfinance 分析師預估寫入 estimates 表 | S-05 | 中 |
| T-06 | 上櫃小票替代資料源（MOPS / 手動補檔） | D-04 | 中 |
| T-07 | 股價警示（漲跌 ±5%、成交量異常） | — | 低 |
| T-08 | Google Sheets 雙向同步（可選） | — | 低 |
| T-09 | 年度 EPS 圖表 | F-07 | 低 |
| T-10 | Dashboard _dark mode 優化 | — | 低 |

---

## 已完成 ✅

| ID | 項目 | 完成日 | 對應需求 |
|----|------|--------|----------|
| T-11 | 專案骨架與 settings 供應鏈種子資料 | 2026-07-03 | D-03 |
| T-12 | Supabase schema migration | 2026-07-03 | S-01 |
| T-13 | yfinance 每日股價 + MA20 同步 | 2026-07-03 | F-03, F-04, S-02 |
| T-14 | 歷史股利同步 | 2026-07-03 | F-06, S-04 |
| T-15 | 殖利率自動計算與每日快照 | 2026-07-03 | F-05, S-03 |
| T-16 | 歷史 EPS（季度）同步 | 2026-07-03 | F-07, S-04 |
| T-17 | Streamlit Dashboard（總覽/供應鏈/個股） | 2026-07-03 | F-01, F-02 |
| T-18 | 手動「立即更新」按鈕 | 2026-07-03 | F-08 |
| T-19 | GitHub Actions 每日排程 | 2026-07-03 | P-01, P-02, P-03 |
| T-20 | GitHub repo 建立與 Secrets | 2026-07-03 | P-01 |
| T-21 | 文件：requirement / USER_GUIDE / CHANGELOG | 2026-07-03 | — |
| T-22 | 上櫃 .TWO / 盟立 2474 代號修正 | 2026-07-03 | — |
| T-24 | TW/TWO 代號自動 fallback | 2026-07-03 | B-01 |
| T-25 | 本益比 pe_ratio 同步與 Dashboard 顯示 | 2026-07-03 | — |
| T-26 | 均線狀態 MA5/MA20/MA60 雙欄 | 2026-07-03 | — |
| T-27 | 長期股價累積（730天+增量） | 2026-07-03 | — |

---

## 已知問題 🐛

| ID | 問題 | 影響標的 | 狀態 |
|----|------|----------|------|
| B-01 | yfinance 上櫃代號 TW/TWO 不一致 | 已修復：symbol_resolver + settings 修正 | ✅ 已解決 |
| B-02 | yfinance 無法取得 5371 中光電 | 改為 5371.TWO | ✅ 已解決 |

---

## 變更紀錄

詳見 [CHANGELOG.md](CHANGELOG.md)
