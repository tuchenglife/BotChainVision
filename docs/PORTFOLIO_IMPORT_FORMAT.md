# 投資帳戶匯入格式規格

> 目標：把富邦、永豐、新光等券商匯出檔整理成共用格式，之後可產生「我的投資帳戶」專區、月度損益與年度報表。

## 匯入原則

- UI 只顯示券商名稱：`富邦`、`永豐`、`新光`，不顯示券商帳號。
- 券商原始檔若含帳號，parser 直接丟棄；若未來需要區分同券商多帳戶，再使用內部 `account_alias`。
- 已實現損益與股利所得分開存放，月報再加總。
- 未實現損益只進庫存快照，不併入已實現月報。
- 日期一律轉成西元 `YYYY-MM-DD`；民國年如 `115/06/12` 轉為 `2026-06-12`。
- 金額一律轉成數字，移除千分位逗號、`--` 轉為空值。

## 1. 已實現損益標準格式

檔案用途：賣出後已確定的資本利得/損失。

| 欄位 | 型別 | 說明 |
|---|---|---|
| broker | text | 券商：`富邦` / `永豐` / `新光` |
| trade_date | date | 成交日 |
| symbol | text | 股票代號 |
| stock_name | text | 股票名稱 |
| trade_type | text | 原始交易類別，如 `現賣`、`現股` |
| quantity | number | 成交股數 |
| sell_price | number | 賣出單價 |
| buy_amount | number | 買入成本或沖銷成本 |
| sell_amount | number | 賣出金額 |
| fee | number | 手續費 |
| tax | number | 交易稅 |
| net_amount | number | 淨收付 |
| realized_pnl | number | 已實現損益（資本利得） |
| return_pct | number | 報酬率百分比，例如 `15.85` 表示 15.85% |
| order_id | text | 委託書號/委託單號 |
| currency | text | 幣別，統一為 `TWD` |
| source_broker_report | text | 原始報表類型 |

### 新光已實現損益 CSV 對應

來源：`新光證交易紀錄_已實現損益0703.csv`

| 標準欄位 | 新光欄位 | 備註 |
|---|---|---|
| broker | 固定 `新光` | 不匯入帳號 |
| trade_date | 成交日期 | 民國年轉西元 |
| symbol | 代號 |  |
| stock_name | 股票 |  |
| trade_type | 類別 | 例：`現賣` |
| quantity | 成交股數 |  |
| sell_price | 單價 |  |
| sell_amount | 價金 |  |
| fee | 手續費 |  |
| tax | 交易稅 |  |
| net_amount | 淨收付 |  |
| realized_pnl | 損益 | 券商已算好的資本利得 |
| return_pct | 報酬率 | 原始值已是百分比數字 |
| order_id | 委託書號 |  |
| currency | 幣別 | `台幣` 轉 `TWD` |

可推算欄位：

- `buy_amount = net_amount - realized_pnl`
- `avg_cost_price = 沖銷均價` 可保留為補充欄位

### 永豐已實現損益 Excel 對應

來源：`永豐已實現損益20260704.xlsx`

| 標準欄位 | 永豐欄位 | 備註 |
|---|---|---|
| broker | 固定 `永豐` | 不匯入帳號 |
| trade_date | 成交日 | 已是西元日期 |
| symbol | 股票代碼 |  |
| stock_name | 股票名稱 |  |
| trade_type | 交易別 | 例：`現股` |
| quantity | 成交數量 |  |
| sell_price | 成交價格 |  |
| buy_amount | 買進金額 |  |
| sell_amount | 賣出金額 |  |
| realized_pnl | 損益 | 券商已算好的資本利得 |
| return_pct | 報酬率 | 原始值為小數，匯入時乘以 100 |
| order_id | 委託單號 |  |
| currency | 幣別 | `台幣` 轉 `TWD` |

### 富邦已實現損益 CSV 對應

來源：`富邦已實現損益20260704.csv`

| 標準欄位 | 富邦欄位 | 備註 |
|---|---|---|
| broker | 固定 `富邦` | 不匯入帳號 |
| trade_date | 交易日 | 已是西元日期 |
| symbol | 股票名稱 | 從括號拆出代號，例如 `彰銀(2801)` -> `2801` |
| stock_name | 股票名稱 | 括號前文字，例如 `彰銀(2801)` -> `彰銀` |
| trade_type | 交易類別 | 例：`現股` |
| quantity | 股數 |  |
| sell_price | 交易價格 |  |
| buy_amount | 買入成本 |  |
| sell_amount | 賣出所得 |  |
| realized_pnl | 已實現損益 | 券商已算好的資本利得 |
| return_pct | 報酬率 | 目前檔案為空，可空值 |
| currency | 固定 `TWD` | 原始檔未提供幣別 |

富邦此檔未提供手續費、交易稅、淨收付與委託單號；匯入時保留空值。

## 2. 庫存/未實現損益標準格式

檔案用途：某一天的庫存快照與即時未實現損益。

| 欄位 | 型別 | 說明 |
|---|---|---|
| broker | text | 券商 |
| snapshot_date | date | 庫存快照日期，優先從檔名或報表時間取得 |
| symbol | text | 股票代號 |
| stock_name | text | 股票名稱 |
| position_type | text | 類別，如普通/現股 |
| quantity | number | 庫存股數 |
| available_quantity | number | 可賣股數 |
| market_price | number | 市價 |
| market_value | number | 市值 |
| avg_cost_price | number | 成本價 |
| trade_avg_price | number | 成交均價 |
| cost_basis | number | 成本 |
| unrealized_pnl | number | 未實現損益 |
| return_pct | number | 未實現報酬率百分比 |
| estimated_net_amount | number | 預估淨收付 |
| fee_estimate | number | 預估手續費 |
| currency | text | 幣別 |

### 新光庫存 CSV 對應

來源：`新光證庫存_0703.csv`

| 標準欄位 | 新光欄位 | 備註 |
|---|---|---|
| broker | 固定 `新光` | 原始帳號欄丟棄 |
| snapshot_date | 檔名 `0703` 或匯入日 | 後續可由使用者指定年份 |
| symbol | 股號 |  |
| stock_name | 商品 |  |
| position_type | 類別 |  |
| quantity | 股數 |  |
| available_quantity | 可用股數 |  |
| market_price | 市價 |  |
| market_value | 市值 |  |
| avg_cost_price | 成本價 | 除權息後調整成本 |
| trade_avg_price | 成交均價 | 原始買進平均參考 |
| cost_basis | 成本 |  |
| unrealized_pnl | 預估損益 |  |
| return_pct | 報酬率(%) |  |
| estimated_net_amount | 預估淨收付 |  |
| fee_estimate | 手續費 |  |
| currency | 幣別 | `TWD` |

### 永豐庫存/未實現損益 Excel 對應

來源：`永豐未實現損益20260704.xlsx`

| 標準欄位 | 永豐欄位 | 備註 |
|---|---|---|
| broker | 固定 `永豐` | 不匯入帳號 |
| snapshot_date | 檔名 `20260704` 或匯入日 | 建議優先使用檔名日期 |
| symbol | 代碼 | 保留文字格式；ETF 可能有前導零或英文字母，如 `00403A`、`00981A` |
| stock_name | 股票名稱 |  |
| position_type | 類別 | 例：`現股` |
| quantity | 昨日餘額 | 永豐此檔以昨日餘額作庫存股數 |
| available_quantity | 空值 | 原始檔未提供可用股數 |
| market_price | 現價 |  |
| market_value | 現值 |  |
| avg_cost_price | 成本均價 |  |
| trade_avg_price | 空值 | 原始檔未提供成交均價 |
| cost_basis | 付出成本 |  |
| unrealized_pnl | 損益試算 |  |
| return_pct | 獲利率 | 原始值為小數，匯入時乘以 100 |
| estimated_net_amount | 現值 | 未提供預估淨收付，先以現值作參考 |
| currency | 幣別 | `台幣` 轉 `TWD` |

永豐未實現檔另有 `融資金額`、`融券保證`，可作為補充欄位保留。

### 富邦未實現損益 CSV 對應

來源：`富邦未實現損益20260704.csv`

| 標準欄位 | 富邦欄位 | 備註 |
|---|---|---|
| broker | 固定 `富邦` | 不匯入帳號 |
| snapshot_date | 檔名 `20260704` 或匯入日 | 建議優先使用檔名日期 |
| symbol | 證券名稱 | 從括號拆出代號，例如 `台積電(2330)` -> `2330` |
| stock_name | 證券名稱 | 括號前文字，例如 `台積電(2330)` -> `台積電` |
| position_type | 類別 | 例：`現股` |
| quantity | 即時庫存(股) |  |
| available_quantity | 空值 | 富邦此檔未提供可用股數 |
| market_price | 現價 |  |
| market_value | 資產市值 |  |
| avg_cost_price | 成本均價 |  |
| trade_avg_price | 空值 | 富邦此檔未提供成交均價 |
| cost_basis | 付出成本 |  |
| unrealized_pnl | 原幣損益試算 |  |
| return_pct | 獲利率 | 移除 `%` 後轉數字 |
| estimated_net_amount | 淨值 | 富邦欄位名稱為 `淨值` |
| currency | 幣別 | `TWD` |

富邦未實現檔另有 `昨日餘額`、`今買成(股)`、`今賣成(股)`、`融資金額`，可作為補充欄位保留。

## 3. 股利所得標準格式

檔案用途：月報與年度報表中的股利所得，不併入資本利得。

| 欄位 | 型別 | 說明 |
|---|---|---|
| broker | text | 券商 |
| ex_dividend_date | date | 除息/除權日 |
| pay_date | date | 入帳日，若券商未提供可空白 |
| symbol | text | 股票代號 |
| stock_name | text | 股票名稱 |
| quantity | number | 除息基準股數 |
| dividend_per_share | number | 每股股利 |
| dividend_income | number | 股利所得 |
| currency | text | 幣別 |
| source_broker_report | text | 原始報表類型 |

富邦截圖中的「股利試算」應匯入此表；富邦「已實現損益」與「即時未實現損益」不含股利所得。

## 4. 月度報表計算

月度報表由標準表計算，不直接使用券商報表總計。

| 指標 | 計算方式 |
|---|---|
| 資本利得 | `sum(realized_pnl)`，依 `trade_date` 歸月 |
| 股利所得 | `sum(dividend_income)`，依 `ex_dividend_date` 歸月 |
| 已實現總損益 | 資本利得 + 股利所得 |
| 月底未實現損益 | 該月最後一筆庫存快照 `sum(unrealized_pnl)` |
| 總資產市值 | 該月最後一筆庫存快照 `sum(market_value)` |

## 5. 目前已確認檔案

| 檔案 | 狀態 | 用途 |
|---|---|---|
| `D:\Tina\股務\新光證交易紀錄_已實現損益0703.csv` | 已解析 | 新光已實現損益 |
| `D:\Tina\股務\新光證庫存_0703.csv` | 已解析 | 新光庫存 |
| `D:\Tina\股務\永豐已實現損益20260704.xlsx` | 已解析 | 永豐已實現損益 |
| `D:\Tina\股務\永豐未實現損益20260704.xlsx` | 已解析 | 永豐庫存/未實現損益 |
| `D:\Tina\股務\富邦已實現損益20260704.csv` | 已解析 | 富邦已實現損益 |
| `D:\Tina\股務\富邦未實現損益20260704.csv` | 已解析 | 富邦庫存/未實現損益 |

