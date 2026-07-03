# Changelog

本專案所有重要變更依日期記錄於此。  
格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)。

---

## [Unreleased]

### 待發布
- 新聞 RSS 聚合與預估 EPS/營收抽取

---

## [0.2.0] - 2026-07-03

### Added
- `src/symbol_resolver.py` — 自動嘗試 `.TW` / `.TWO` 解析 yfinance 代號
- `src/fundamentals.py` — 本益比（trailingPE / 股價÷EPS）
- `daily_prices.pe_ratio`、`eps_ttm` 欄位（migration 003）
- 總覽：公司名稱、前一天收盤、短線/中線狀態、本益比、漲跌配色
- 個股：中文公司名、類別、MA5/MA20/MA60、本益比
- 「元件分布」分頁
- 「關於」均線狀態說明

### Fixed
- 1597 等上櫃股：改用正確 yfinance 後綴（多數為 `.TW`）
- 5371 中光電：改為 `5371.TWO`
- Cache 對話框：移除 `st.cache_data.clear()`
- NaN 值寫入 Supabase JSON 錯誤

### Changed
- 首次同步回補 730 天；每日增量累積保留歷史
- 同步成功 **20 檔標的、14580 筆**股價（零錯誤）

---

## [0.1.0] - 2026-07-03

### Added
- 專案初始化：BotChainVision 人形機器人台股供應鏈 Dashboard
- `settings/supply_chain_categories.json` — 5 大關鍵技術分類
- `settings/supply_chain_vendors.json` — 20 筆供應鏈廠商（18 檔唯一標的）
- Supabase PostgreSQL schema（`supabase/migrations/001_initial_schema.sql`）
  - `daily_prices` — 股價 OHLCV + MA20
  - `dividend_yield_daily` — 每日殖利率快照
  - `dividends` — 歷史現金股利
  - `historical_eps` — 季度 EPS
  - `estimates` / `news_articles` — 預留新聞與預估
  - `supply_chain_vendors` / `supply_chain_categories`
  - `sync_log` — 同步紀錄
- `src/sync.py` — yfinance 資料同步核心
  - `run_full_sync()` 供排程與手動按鈕共用
  - 殖利率公式：近 12 月股利 ÷ 收盤價 × 100
- `scripts/daily_sync.py` — CLI 同步入口
- `scripts/run_migration.py` — 本機套用 SQL migration
- `app/streamlit_app.py` — Dashboard
  - 總覽 / 供應鏈 / 個股詳情 三分頁
  - 股價 + MA20 圖、殖利率走勢、股利表、EPS 表
  - 「立即更新股價與殖利率」按鈕
- `.github/workflows/daily_sync.yml` — 週一至五 UTC 10:00 自動同步
- 文件：`requirement.md`、`docs/USER_GUIDE.md`、`TODO.md`、`CHANGELOG.md`

### Changed
- 盟立代號由 2464 更正為 **2474**（上市）
- 上櫃標的 `market` 設為 `TWO`（yfinance 格式）
- EPS 抓取改用 `quarterly_income_stmt`（取代已棄用 API）
- 同步邏輯：單一 ticker 失敗記錄錯誤，不阻斷其他標的

### Fixed
- Supabase URL 使用正確網域 `*.supabase.co`
- RLS 政策：anon 角色可讀取（Dashboard 未來可用 anon key）

### Security
- `.gitignore` 排除 `.env`、`supabase.txt`
- GitHub Secrets：`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`

### Data
- 首次手動同步寫入 **1260** 筆股價紀錄（90 日 × 多檔標的）
- 6 檔標的 yfinance 暫無資料（見 TODO.md B-01, B-02）

### Infrastructure
- Supabase 專案：`verzhajfabdmnkmedjfo`（botchain-vision）
- GitHub repo：https://github.com/tuchenglife/BotChainVision
- GitHub Actions：https://github.com/tuchenglife/BotChainVision/actions
- 本機 Dashboard：http://localhost:8501（已驗證可啟動）
- 雲端 Dashboard（待部署）：https://botchainvision.streamlit.app — 見 [docs/DEPLOY_STREAMLIT.md](docs/DEPLOY_STREAMLIT.md)

### Documentation
- `requirement.md` — 需求規格
- `docs/USER_GUIDE.md` — 使用者指南（登入網址）
- `TODO.md` — 待辦追蹤
- `CHANGELOG.md` — 變更紀錄
- `docs/GITHUB_SECRETS_SETUP.md` — GitHub Secrets 設定
- `scripts/setup_github_secrets.ps1` — 本機一鍵設定 Secrets

---

## 版本對照

| 版本 | 日期 | 說明 |
|------|------|------|
| 0.1.0 | 2026-07-03 | MVP：股價、MA20、殖利率、股利、EPS、供應鏈地圖 |

---

## 相關連結

- [需求規格](requirement.md)
- [使用者指南](docs/USER_GUIDE.md)
- [待辦事項](TODO.md)
