# 加密貨幣監控推播機器人 — 專案企劃書

> **文件版本**：v1.2  
> **建立日期**：2026-06-07  
> **主要技術**：Python · Telegram Bot · 爬蟲 · 自動化交易  
> **協作方式**：本文件供 LLM 協作開發使用，各節均可獨立作為任務上下文

---

## 目錄

1. [專案概述](#1-專案概述)
2. [開發階段規劃](#2-開發階段規劃)
3. [功能需求清單](#3-功能需求清單)
4. [技術架構設計](#4-技術架構設計)
5. [專案資料夾結構](#5-專案資料夾結構)
6. [技術選型說明](#6-技術選型說明)
7. [資料來源清單](#7-資料來源清單)
8. [風險評估](#8-風險評估)
9. [開發起點建議](#9-開發起點建議)

---

## 1. 專案概述

### 目標

建立一個全自動的加密貨幣監控系統，定期抓取鏈上與市場資料，透過 Telegram Bot 推播關鍵訊號，並逐步延伸至策略分析與自動交易。

### 核心價值

- **即時性**：掌握市場動向，不錯過重要訊號
- **自動化**：排程執行，無需手動查看
- **可擴充**：模組化設計，功能可獨立迭代
- **可協作**：程式碼結構清晰，便於 LLM 輔助開發

### 技術定位

| 面向 | 選擇 |
|------|------|
| 主要語言 | Python 3.11+ |
| 資料抓取 | API + 爬蟲（httpx / Playwright） |
| 推播管道 | Telegram Bot API |
| 排程方式 | APScheduler（本地）/ cron（部署） |
| 資料儲存 | SQLite → PostgreSQL |
| 部署環境 | Docker + VPS 或本地長跑 |

---

## 2. 開發階段規劃

### Phase 1 — 核心基礎（預估 2–3 週）

**目標**：讓 Telegram Bot 真的能打訊息給你，跑通最小可用版本。

**里程碑**：
- Telegram Bot 成功接收 `/price BTC` 指令並回覆
- 排程每 5 分鐘自動推播 BTC/ETH 價格與漲跌幅
- 啟動時自動推播 Bot 上線通知與第一則市場快報
- Alternative.me Fear & Greed 指數整合完成
- 基本錯誤處理與日誌記錄

### Phase 2 — 分析增強（預估 3–4 週）

**目標**：加入技術指標、歷史資料、用戶自訂警報。

**里程碑**：
- RSI、MACD 基礎指標模組完成
- SQLite 儲存 K 線歷史資料（至少 30 天）
- CoinGecko OHLC 歷史資料可同步寫入 SQLite
- 用戶可透過 Bot 設定價格突破警報
- 圖表圖片可傳送至 Telegram

### Phase 3 — 智能進化（預估 4–6 週）

**目標**：AI 輔助分析、模擬交易、真實下單。

**里程碑**：
- Claude API 生成市場摘要文字推播
- Paper Trading 模擬下單紀錄
- Binance Testnet 真實 API 連線測試
- 停損保護機制上線

---

## 3. 功能需求清單

### Phase 1 功能

| 功能 | 說明 | 優先級 |
|------|------|--------|
| 價格抓取 | BTC、ETH 及自訂幣種即時價格、24h 漲跌幅、交易量、市值 | P0 |
| Telegram Bot 建立 | Bot Token 申請、webhook/polling 設定、基本指令處理 | P0 |
| 定時推播 | 每 N 分鐘/小時自動推播市場摘要 | P0 |
| Fear & Greed | 整合 Alternative.me 市場情緒指數 | P1 |
| CoinAnk 爬蟲 | 抓取資金費率（Funding Rate）、多空比等衍生品資料 | P2 |
| 錯誤處理 | API 失敗重試、Bot 異常通知、日誌記錄 | P1 |
| 設定檔管理 | `.env` 儲存 Token、`config.yaml` 管理幣種與排程 | P1 |
| 訊息格式化 | 清晰的推播格式，含 emoji、漲跌顏色符號 | P2 |

### Phase 2 功能

| 功能 | 說明 | 優先級 |
|------|------|--------|
| 技術指標 | RSI、MACD、布林帶、ATR（使用 pandas-ta） | P0 |
| 歷史資料儲存 | SQLite 儲存 OHLCV K 線，支援多幣種多時框 | P0 |
| 價格警報 | 用戶設定突破條件，觸發時立即推播 | P0 |
| 多幣種篩選 | 24h 漲幅 Top 10、成交量異動等篩選推播 | P1 |
| 圖表生成 | K 線圖 + 指標疊加，以圖片傳至 Telegram | P1 |
| 用戶訂閱制 | 每位用戶可自訂追蹤幣種與推播頻率 | P1 |
| Fear & Greed | Alternative.me 恐懼貪婪指數整合 | P2 |

### Phase 3 功能

| 功能 | 說明 | 優先級 |
|------|------|--------|
| AI 市場摘要 | 呼叫 Claude API，生成每日市場解讀文字 | P0 |
| 策略信號組合 | 多指標交叉驗證，生成買/賣/觀望信號 | P0 |
| Paper Trading | 模擬下單、持倉、損益記錄，無真實資金風險 | P0 |
| 交易所連線 | CCXT 接入 Binance/OKX，支援現貨與合約 | P1 |
| 自動下單 | 限價/市價下單 + 停損/停利設定 | P1 |
| 投資組合追蹤 | 持倉成本、損益、佔比報表 | P1 |
| 異常偵測 | 暴跌/插針/爆倉警報（閾值觸發） | P2 |
| Web Dashboard | 簡易管理介面，查看推播紀錄與持倉狀況 | P2 |

---

## 4. 技術架構設計

### 系統架構圖（文字版）

```
┌─────────────────────────────────────────────────────┐
│                   資料來源層                          │
│  CoinGecko API  Binance WS  CoinAnk爬蟲  Fear&Greed │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   資料處理層                          │
│    資料清洗  指標計算(pandas-ta)  異常過濾             │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌────▼──────────┐
│   排程層      │ │  儲存層   │ │   分析層      │
│ APScheduler  │ │ SQLite/PG │ │ 策略 / Claude │
└───────┬──────┘ └─────┬─────┘ └────┬──────────┘
        │              │             │
┌───────▼──────────────▼─────────────▼──────────┐
│                   推播層                        │
│          python-telegram-bot (async)           │
└────────────────────────────────────────────────┘
```

### 資料流說明

1. **排程觸發** → APScheduler 依設定間隔喚醒任務
2. **資料抓取** → API 呼叫或爬蟲取得最新行情
3. **資料處理** → 清洗、計算指標、比對警報條件
4. **條件判斷** → 是否符合推播條件（定時 or 觸發式）
5. **推播執行** → 格式化訊息，透過 Telegram Bot 送出
6. **資料儲存** → 將原始 K 線與計算結果存入資料庫

---

## 5. 專案資料夾結構

```
crypto-bot/
│
├── .env                        # 敏感設定（不進 git）
├── .env.example                # 設定範本
├── config.yaml                 # 幣種、排程、警報設定
├── requirements.txt            # Python 依賴
├── docker-compose.yml          # 部署設定
├── README.md
│
├── bot/                        # Telegram Bot 相關
│   ├── __init__.py
│   ├── main.py                 # Bot 入口、啟動
│   ├── handlers/               # 指令處理器
│   │   ├── commands.py         # /start /price /help
│   │   ├── alerts.py           # /setalert /listalerts
│   │   └── subscribe.py        # /subscribe /unsubscribe
│   └── formatters.py           # 訊息格式化工具
│
├── data/                       # 資料抓取模組
│   ├── __init__.py
│   ├── coingecko.py            # CoinGecko API 封裝
│   ├── binance_ws.py           # Binance WebSocket 串流
│   ├── coinank_scraper.py      # CoinAnk 爬蟲
│   ├── fear_greed.py           # Alternative.me 恐懼貪婪指數
│   └── base.py                 # 基礎類別、重試裝飾器
│
├── analysis/                   # 分析與策略模組
│   ├── __init__.py
│   ├── indicators.py           # 技術指標計算（目前為內建 SMA/EMA/RSI/MACD）
│   ├── signals.py              # 買賣信號生成邏輯
│   ├── screener.py             # 多幣種篩選器
│   └── ai_summary.py          # Claude API 市場摘要（Phase 3）
│
├── storage/                    # 資料儲存模組
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy 設定、連線管理
│   ├── models.py               # ORM 資料表定義
│   ├── candles.py              # K 線資料 CRUD
│   └── users.py                # 用戶設定 CRUD
│
├── scheduler/                  # 排程模組
│   ├── __init__.py
│   ├── jobs.py                 # 定義所有排程任務
│   └── runner.py               # APScheduler 設定與啟動
│
├── trading/                    # 交易模組（Phase 3）
│   ├── __init__.py
│   ├── exchange.py             # CCXT 交易所介面
│   ├── paper_trading.py        # 模擬交易
│   ├── order_manager.py        # 下單 / 停損管理
│   └── portfolio.py            # 持倉追蹤
│
├── charts/                     # 圖表生成
│   ├── __init__.py
│   └── candlestick.py          # K 線圖 + 指標疊加
│
├── utils/                      # 通用工具
│   ├── __init__.py
│   ├── logger.py               # 日誌設定
│   ├── cache.py                # 簡易快取（記憶體 or Redis）
│   └── config_loader.py        # 設定檔載入
│
└── tests/                      # 測試
    ├── test_data.py
    ├── test_indicators.py
    └── test_formatters.py
```

---

## 6. 技術選型說明

### 資料抓取層

| 工具 | 用途 | 選用原因 |
|------|------|----------|
| `httpx` | 非同步 HTTP 請求 | async 支援，比 requests 更適合排程場景 |
| `playwright` | 動態頁面爬蟲 | CoinAnk 等 JS 渲染頁面的備用方案 |
| `beautifulsoup4` | HTML 解析 | 靜態頁面爬蟲首選，輕量易用 |
| `websockets` | WebSocket 連線 | Binance 即時串流 |
| `tenacity` | 重試機制 | 優雅處理 API 失敗，支援指數退避 |

### 排程與非同步層

| 工具 | 用途 | 選用原因 |
|------|------|----------|
| `APScheduler` | 定時任務 | 支援 interval / cron，整合 asyncio |
| `asyncio` | 非同步執行 | 避免 I/O 阻塞，提升並發效率 |
| `aiohttp` | 非同步 HTTP（備選） | 高並發場景替代 httpx |

### 分析層

| 工具 | 用途 | 選用原因 |
|------|------|----------|
| `SQLAlchemy` | ORM / Async DB | 建立 SQLite/未來 PostgreSQL 的統一儲存介面 |
| `aiosqlite` | Async SQLite Driver | 與 SQLAlchemy async 搭配，作為 Phase 2 本地資料庫 |
| `pandas` | 時序資料處理 | OHLCV 操作的標準工具（後續擴充） |
| `pandas-ta` | 技術指標 | 一行呼叫 130+ 指標，無需手寫公式（後續擴充） |
| `numpy` | 數值計算 | pandas 底層依賴，信號過濾用（後續擴充） |
| `ccxt` | 交易所資料 | 統一介面抓 100+ 交易所 K 線（Phase 2+） |
| `anthropic` | Claude API | AI 市場摘要與異常解讀（Phase 3） |

### 推播層

| 工具 | 用途 | 選用原因 |
|------|------|----------|
| `python-telegram-bot` v20+ | Telegram Bot | 最成熟的 Python Telegram 函式庫，支援 async |
| `matplotlib` / `mplfinance` | 圖表生成 | K 線圖轉圖片推播 |

### 儲存層

| 工具 | 用途 | 選用原因 |
|------|------|----------|
| `SQLite` | Phase 2 本地資料庫 | 零配置，適合開發與單機部署 |
| `PostgreSQL` | Phase 2+ 生產資料庫 | 支援大量時序資料，擴充性佳 |
| `SQLAlchemy` | ORM | 統一資料庫操作介面，方便切換 DB |
| `Redis`（可選） | 快取 + 任務佇列 | 避免重複 API 呼叫，Celery 搭配用 |

### 部署層

| 工具 | 用途 | 選用原因 |
|------|------|----------|
| `Docker` | 容器化部署 | 環境一致，搭配 restart policy 保持長跑 |
| `python-dotenv` | 環境變數管理 | 敏感資訊與程式碼分離 |
| `loguru` | 日誌管理 | 比 logging 模組更簡潔，支援結構化日誌 |

---

## 7. 資料來源清單

### 免費 API（推薦優先使用）

| 來源 | 資料類型 | 限制 | 說明 |
|------|----------|------|------|
| CoinGecko | 價格、市值、交易量、歷史 K 線 | 30 req/min（免費） | 最穩定的免費加密貨幣 API |
| Alternative.me | 恐懼貪婪指數 | 無明顯限制 | 簡單易用 |
| Binance Public API | K 線、深度、成交 | 1200 req/min | 免登入即可使用 |
| Binance WebSocket | 即時 Tick、K 線串流 | - | 適合需要低延遲的場景 |

### 需爬蟲的頁面

| 來源 | 資料類型 | 爬蟲難度 | 說明 |
|------|----------|----------|------|
| CoinAnk | 資金費率、多空比、大額清算 | 中（需處理 JS 渲染） | 衍生品市場重要資料 |
| CryptoQuant | 鏈上資料（交易所流入流出） | 中高（部分需登入） | 需要評估是否付費 |
| LookIntoBitcoin | 比特幣週期指標（彩虹圖等） | 低（靜態頁面） | 週期分析參考 |

### 付費 API（Phase 2+ 可考慮）

| 來源 | 資料類型 | 費用 |
|------|----------|------|
| Glassnode | 完整鏈上資料 | $29+/月 |
| CoinGecko Pro | 更高速率限制 | $129+/月 |
| Kaiko | 機構級市場資料 | 詢價 |

---

## 8. 風險評估

### 技術風險

| 風險 | 等級 | 因應措施 |
|------|------|----------|
| API 速率限制 / 封鎖 | 高 | 實作 cache 層（Redis 或記憶體），設置請求間隔，必要時 IP 輪換 |
| CoinAnk 爬蟲失效 | 高 | 監控 HTML 結構變化，設置備援資料來源，爬蟲失敗改用 API 替代 |
| Bot 推播中斷 | 中 | Docker restart policy，Telegram 連線重試，錯誤通知備用頻道 |
| 資料庫資料遺失 | 中 | 定期備份（cron + pg_dump），重要資料雙重寫入 |
| 時區與時間戳錯誤 | 低 | 統一使用 UTC 儲存，顯示時再轉換台灣時間 |

### 財務風險（Phase 3 自動交易）

| 風險 | 等級 | 因應措施 |
|------|------|----------|
| 策略邏輯錯誤導致連續虧損 | 極高 | 強制 Paper Trading 至少 1 個月後才上真實資金 |
| API Key 洩漏 | 高 | API Key 僅開放交易權限（不開提幣），存 `.env` 不進 git |
| 網路中斷導致掛單無法取消 | 中 | 實作心跳機制，中斷超過 N 秒自動取消所有掛單 |
| 真實下單金額設定錯誤 | 中 | 設定單筆最大下單金額上限（hard limit），程式碼層強制校驗 |

### 法規風險

- 自動交易可能受所在地法規限制，上線前請確認當地規定
- 使用交易所 API 需同意其使用條款，確認不違反其機器人政策

---

## 9. 開發起點建議

### 環境準備清單

```bash
# 1. Python 環境
python --version  # 需 3.11+
pip install virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 申請 Telegram Bot Token
# → 在 Telegram 搜尋 @BotFather
# → 送出 /newbot，依指示取得 TOKEN

# 3. 建立 .env 檔案
TELEGRAM_BOT_TOKEN=your_token_here
COINGECKO_API_KEY=           # 免費版可留空
BINANCE_API_KEY=             # Phase 3 才需要
BINANCE_SECRET_KEY=          # Phase 3 才需要
```

### Phase 1 最小可用版本（MVP）起手步驟

1. `bot/main.py` — 建立 Bot，處理 `/start` 與 `/price BTC`
2. `data/coingecko.py` — 封裝 CoinGecko 價格查詢
3. `data/fear_greed.py` — 整合市場情緒指數
4. `scheduler/jobs.py` — 加入啟動即時推播與每 5 分鐘推播任務
5. `bot/formatters.py` — 格式化推播訊息

### requirements.txt（Phase 1 基本版）

```
python-telegram-bot==21.9
httpx==0.27.0
APScheduler==3.10.4
python-dotenv==1.0.1
pyyaml==6.0.1
tenacity==8.3.0
loguru==0.7.2
SQLAlchemy==2.0.41
aiosqlite==0.21.0
```

### 已完成現況（截至 2026-06-07）

- Bot 啟動後會主動推播「已上線通知」
- Bot 啟動後會立即推送第一則市場快報，不需等第一個排程週期
- `/price` 支援 `BTC`、`btc`、`BTCUSDT` 這類常見輸入
- `/price` 回覆包含價格、24h 漲跌、24h 區間、成交量、市值、資料時間
- `/fear` 可查詢最新 Fear & Greed 指數
- 已建立 `storage/` 模組，使用 `SQLite + SQLAlchemy async` 儲存 K 線
- 已建立 `analysis/indicators.py`，包含 `SMA / EMA / RSI / MACD`
- 已建立 CoinGecko OHLC 同步流程，可將追蹤幣種歷史 K 線寫入 SQLite

### 推播訊息格式範例

```
📊 市場快報 2026-06-07 14:30 (UTC+8)

₿ BTC   $67,234  🟢 +2.41%
Ξ ETH   $3,512   🔴 -0.83%
◎ SOL   $142.3   🟢 +5.20%

😱 恐懼貪婪指數：62（貪婪）
💰 BTC 資金費率：+0.012%

─────────────────
⚠️ 警報觸發：ETH 跌破 $3,500 支撐位
```

---

## 附錄：LLM 協作提示詞模板

在與 LLM 協作開發時，可使用以下提示詞框架快速切入各模組：

```
角色：你是一位 Python 後端工程師，熟悉加密貨幣資料抓取與 Telegram Bot 開發。

專案背景：參考 crypto_bot_project_plan.md 的架構設計。

當前任務：實作 [模組名稱]，位於 [檔案路徑]。

需求：
- [具體功能描述]
- 需相容 Python 3.11+，使用 async/await
- 包含基本錯誤處理與 loguru 日誌

請先說明實作思路，再給出完整程式碼。
```
