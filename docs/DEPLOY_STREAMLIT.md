# Streamlit Cloud 部署指南

## 一次性部署步驟

1. **確認 GitHub repo 已推送**  
   https://github.com/tuchenglife/BotChainVision

2. **登入 Streamlit Community Cloud**  
   https://share.streamlit.io （使用 GitHub 帳號 `tuchenglife` 登入）

3. **Create app**
   - Repository: `tuchenglife/BotChainVision`
   - Branch: `main`
   - Main file path: `app/streamlit_app.py`

4. **Advanced settings → Secrets**（貼上以下內容，key 從 Supabase 取得）

```toml
SUPABASE_URL = "https://verzhajfabdmnkmedjfo.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "你的_service_role_key"
```

5. **Deploy**

6. **記下部署網址**（通常類似以下之一）
   - `https://botchainvision.streamlit.app`
   - `https://tuchenglife-botchainvision-app-streamlit-app-xxx.streamlit.app`

7. **更新文件**：將實際網址寫入 `docs/USER_GUIDE.md` 與 `README.md`

## 驗證

- 開啟雲端網址 → 應看到「BotChainVision」標題
- 點「立即更新股價與殖利率」→ 應成功寫入 Supabase
- 至 Supabase Table Editor 確認 `sync_log` 有 `manual` 紀錄

## 常見問題

| 問題 | 解法 |
|------|------|
| Secrets 錯誤 | 確認 `SUPABASE_SERVICE_ROLE_KEY` 完整、無多餘空格 |
| 模組找不到 | 確認 `requirements.txt` 在 repo 根目錄 |
| App 休眠 | 免費版閒置會休眠，首次開啟需等待數秒 |
