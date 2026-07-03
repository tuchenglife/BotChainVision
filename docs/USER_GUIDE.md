# BotChainVision 使用者指南 (User Guide)

> 人形機器人關鍵零組件 × 台股供應鏈追蹤 Dashboard  
> 最後更新：2026-07-03

---

## 登入與服務網址總覽

| 服務 | 網址 | 用途 | 登入方式 |
|------|------|------|----------|
| **Dashboard（本機）** | http://localhost:8501 | 開發／本機瀏覽 | 無需登入 |
| **Dashboard（雲端）** | https://botchainvision.streamlit.app | 正式使用（手機/任何裝置） | 無需登入（首次需部署，見下方） |
| **Supabase 資料庫** | https://supabase.com/dashboard/project/verzhajfabdmnkmedjfo | 查看資料表、SQL、API 金鑰 | GitHub / Email 登入 Supabase |
| **GitHub 程式庫** | https://github.com/tuchenglife/BotChainVision | 原始碼、Actions 排程 | GitHub 帳號 `tuchenglife` |
| **GitHub Actions** | https://github.com/tuchenglife/BotChainVision/actions | 手動/查看每日同步 | GitHub 登入 |
| **Streamlit Cloud 管理** | https://share.streamlit.io | 部署、Secrets、監控 | GitHub 登入 Streamlit |

### Supabase 專案資訊

| 項目 | 值 |
|------|-----|
| Project Name | botchain-vision |
| Project ID | `verzhajfabdmnkmedjfo` |
| API URL | `https://verzhajfabdmnkmedjfo.supabase.co` |
| Region | （於 Supabase Dashboard 查看） |

> ⚠️ **請勿**將 `service_role` 金鑰分享給他人或公開貼文。僅用於後端同步與 Dashboard 更新按鈕。

---

## 一、日常使用（推薦：雲端 Dashboard）

### 1. 開啟 Dashboard

瀏覽器前往：

```
https://botchainvision.streamlit.app
```

若尚未部署，請先完成下方「首次部署 Streamlit Cloud」。

### 2. 頁面說明

| 分頁 | 功能 |
|------|------|
| **總覽** | 所有觀察標的之收盤、漲跌%、MA20、殖利率 |
| **供應鏈** | 5 大技術分類與對應台股廠商 |
| **個股詳情** | 股價+MA20 圖、殖利率走勢、歷史股利、歷史 EPS |

### 3. 手動更新資料

點擊頁面上方：

```
🔄 立即更新股價與殖利率
```

- 系統會從 yfinance 抓取最新資料
- 自動計算 **MA20**、**殖利率**（近 12 月股利 ÷ 股價）
- 寫入 Supabase 雲端資料庫
- 可選回補天數：30 / 90 / 180 / 365

### 4. 自動更新（不需開電腦）

每個台股交易日約 **18:00（台灣）**，GitHub Actions 自動執行同步。

手動觸發排程：
1. 前往 [Actions](https://github.com/tuchenglife/BotChainVision/actions)
2. 選 **Daily Market Sync** → **Run workflow**

---

## 二、本機使用

### 啟動 Dashboard

```bash
cd D:\Tina\Projects\Cursor\BotChainVision
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

瀏覽器開啟：**http://localhost:8501**

### 本機手動同步（命令列）

```bash
python scripts/daily_sync.py --source manual --backfill-days 90
```

### 環境變數

複製 `.env.example` → `.env`，填入：

```env
SUPABASE_URL=https://verzhajfabdmnkmedjfo.supabase.co
SUPABASE_SERVICE_ROLE_KEY=你的_service_role_key
```

---

## 三、首次部署 Streamlit Cloud（一次性）

1. 前往 https://share.streamlit.io ，用 GitHub 登入
2. **Create app** → 選擇 repo `tuchenglife/BotChainVision`
3. **Main file path**：`app/streamlit_app.py`
4. **Advanced settings → Secrets**，貼上：

```toml
SUPABASE_URL = "https://verzhajfabdmnkmedjfo.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "你的_service_role_key"
```

5. **Deploy**
6. 部署完成後網址通常為 `https://botchainvision.streamlit.app`（或 Streamlit 指派的網址）
7. 將實際網址更新到本文件「Dashboard（雲端）」欄位

---

## 四、新增 / 修改供應鏈廠商

1. 編輯 `settings/supply_chain_vendors.json`
2. 每筆格式：

```json
{
  "category_id": "motor",
  "company": "公司名",
  "ticker": "2308",
  "market": "TW",
  "watch": true
}
```

| market | 說明 | yfinance 範例 |
|--------|------|---------------|
| `TW` | 上市 | `2308.TW` |
| `TWO` | 上櫃 | `4576.TWO` |

3. 推送至 GitHub 或在本機按「立即更新」
4. 同步時會自動 upsert 至 Supabase `supply_chain_vendors` 表

---

## 五、查看雲端資料（Supabase）

1. 登入 https://supabase.com/dashboard/project/verzhajfabdmnkmedjfo
2. **Table Editor** 可查看：

| 資料表 | 內容 |
|--------|------|
| `daily_prices` | 每日股價、MA20 |
| `dividend_yield_daily` | 每日殖利率 |
| `dividends` | 歷史股利 |
| `historical_eps` | 歷史 EPS |
| `supply_chain_vendors` | 供應鏈廠商 |
| `sync_log` | 同步紀錄 |

---

## 六、GitHub Secrets（已設定則跳過）

Repo → **Settings → Secrets and variables → Actions**：

| Secret | 值 |
|--------|-----|
| `SUPABASE_URL` | `https://verzhajfabdmnkmedjfo.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase API → service_role |

---

## 七、常見問題

### Q：殖利率怎麼算的？
**A：** 系統自動計算：`近 12 個月現金股利合計 ÷ 當日收盤價 × 100%`

### Q：為什麼有些股票沒資料？
**A：** yfinance 對部分上櫃小票覆蓋率較低。可確認 `market` 是否為 `TWO`，或待後續改用其他資料源。

### Q：電腦關機會漏資料嗎？
**A：** 不會。GitHub Actions 在雲端每天自動跑。

### Q：Supabase 被 pause 了？
**A：** 到 Dashboard 點 **Restore project**。每日 Actions 寫入可避免自動 pause。

### Q：如何換 Service Role Key？
**A：** Supabase → Project Settings → API → 重新產生，並更新 `.env`、Streamlit Secrets、GitHub Secrets。

---

## 八、相關文件

- [需求規格](../requirement.md)
- [待辦事項](../TODO.md)
- [變更紀錄](../CHANGELOG.md)
