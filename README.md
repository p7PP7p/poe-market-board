---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1005a95e2fac3584a3126ed2e10eee75_ec6f6a4ce33e11f18c5752540024e231
    ReservedCode1: AfdbBsunrGqU2hnjvwPPCif0QIWy/cLFFcuy6BIWIkMG2lOrJM+Uia9i8fFS7vr0coTTUuPxda3FXAlJbP8WYs5NYVY+idhrRZDnMxnxvrJ7N5nDgYNvjrslwouwC+uwKF5OWXhVH4LUIJOBADlUwkLCG0SWVKk4/+xPz1ZNLK+I2DapQNJQSyMA8t0=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1005a95e2fac3584a3126ed2e10eee75_ec6f6a4ce33e11f18c5752540024e231
    ReservedCode2: AfdbBsunrGqU2hnjvwPPCif0QIWy/cLFFcuy6BIWIkMG2lOrJM+Uia9i8fFS7vr0coTTUuPxda3FXAlJbP8WYs5NYVY+idhrRZDnMxnxvrJ7N5nDgYNvjrslwouwC+uwKF5OWXhVH4LUIJOBADlUwkLCG0SWVKk4/+xPz1ZNLK+I2DapQNJQSyMA8t0=
---

# PoE 賽季行情交易榜 · 純網頁方案

目標：**不依賴任何一台電腦開機**，每天自動刷新榜單，打開固定網址即最新。

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `fetch.py` | 抓 poe.ninja 公開 API（純 HTTP，無瀏覽器/無 Cloudflare 攔截），算校正漲跌，產出頁面 |
| `template.html` | 頁面模板（`__LEAGUE__` / `__DATA__` 佔位符，由 fetch.py 注入） |
| `index.html` | **成品頁面**（自包含，資料內嵌，雙擊即可離線查看） |
| `data.json` | 同批資料的 JSON，供其他程式取用 |
| `.github/workflows/daily.yml` | 每日 08:00（北京時間）自動執行 + 提交 + 可選推送微信 |

## 上線三步（GitHub Pages，免費、免伺服器）

1. 新建一個 GitHub repo（public），把本資料夾**全部內容**（含 `.github/`）推上去：
   ```bash
   git init && git add -A && git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<你的帳號>/<repo>.git
   git push -u origin main
   ```
2. repo → Settings → Pages → Source 選 `Deploy from a branch`，Branch 選 `main` / `(root)` → Save。
   約 1 分鐘後網址生效：`https://<你的帳號>.github.io/<repo>/`
3. repo → Settings → Actions → General → Workflow permissions 選 **Read and write permissions**（讓排程能提交新資料）。

之後每天 UTC 00:00（北京 08:00）自動刷新，也可在 Actions 頁面按 `Run workflow` 手動跑一次。

## 推送方式（三選一）

| 方式 | 是否需要憑證 | 說明 |
|---|---|---|
| **A. 收藏固定網址** | 不需要 | 頁面本身就是最新資料，最省事；缺點是要自己打開 |
| **B. Server 醬（微信可收）** | 需 `SERVERCHAN_KEY` | 到 sct.ftqq.com 取得 SendKey，加到 repo → Settings → Secrets → `SERVERCHAN_KEY`；再把 Pages 網址設為 repo Variables 的 `PAGES_URL` |
| **C. Telegram Bot** | 需 token + chat_id | 在 workflow 追加一個 `curl https://api.telegram.org/bot<token>/sendMessage` 步驟 |

工作流已內建 B 的推送步驟，未設定 Secret 時自動跳過，不影響主流程。

## 資料口徑

- 價格：poe.ninja 現值（混沌石計價）
- 原始 7 日漲跌：`sparkline.totalChange`，以神聖石為計價基準
- **真實 7 日漲跌**：`(1+原始漲跌)/(1+神聖石漲跌)-1`，剔除神聖石通膨後的真實購買力變化
- 分類中位數同時給「有變動樣本」與「全體」兩欄（大量裝備 7 日報價不動時，全體中位會退化成神聖石貶值幅度）
- 建議標籤：以真實漲跌 × 同類在售量百分位自動四象限歸類

## 換賽季

修改 `daily.yml` 裡的 `POE_LEAGUE`（或本地執行時設環境變數），賽季名稱取自
`https://poe.ninja/poe1/api/data/index-state` 的 `economyLeagues`。
*（内容由AI生成，仅供参考）*
