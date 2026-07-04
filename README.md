# BotChainVision

人形機器人關鍵零組件 × 台股供應鏈追蹤 Dashboard。

| 文件 | 說明 |
|------|------|
| [使用者指南](docs/USER_GUIDE.md) | **登入網址、日常操作、部署步驟** |
| [需求規格](requirement.md) | 完整功能與資料需求 |
| [待辦事項](TODO.md) | 進度追蹤 |
| [變更紀錄](CHANGELOG.md) | 版本與變更歷史 |

## 快速連結

| 服務 | 網址 |
|------|------|
| Dashboard（雲端） | https://botchainvision-hjt5whpawkhwwwmvfj7dbg.streamlit.app |
| Dashboard（本機） | http://localhost:8501 |
| Supabase | https://supabase.com/dashboard/project/verzhajfabdmnkmedjfo |
| GitHub | https://github.com/tuchenglife/BotChainVision |
| GitHub Actions | https://github.com/tuchenglife/BotChainVision/actions |

## 本機啟動

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## 手動同步

```bash
python scripts/daily_sync.py --source manual
```

## 技術棧

- **前端**：Streamlit + Plotly
- **資料庫**：Supabase (PostgreSQL)
- **股價**：yfinance
- **排程**：GitHub Actions

詳細說明請見 [docs/USER_GUIDE.md](docs/USER_GUIDE.md)。
