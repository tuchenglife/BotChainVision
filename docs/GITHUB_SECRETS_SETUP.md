# GitHub Actions Secrets 設定（一次性）

Repo: https://github.com/tuchenglife/BotChainVision/settings/secrets/actions

## 方式 A — 網頁設定

1. 開啟上方連結 → **New repository secret**
2. 新增：

| Name | Value |
|------|-------|
| `SUPABASE_URL` | `https://verzhajfabdmnkmedjfo.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | 從 Supabase Dashboard → Project Settings → API → `service_role` secret |

## 方式 B — 命令列（在本機終端機執行）

```powershell
cd D:\Tina\Projects\Cursor\BotChainVision
gh secret set SUPABASE_URL --body "https://verzhajfabdmnkmedjfo.supabase.co"
gh secret set SUPABASE_SERVICE_ROLE_KEY --body "你的_service_role_key"
```

設定完成後，至 Actions 手動 Run workflow 測試：
https://github.com/tuchenglife/BotChainVision/actions/workflows/daily_sync.yml
