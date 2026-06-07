# CryptoBot

CryptoBot 是一個加密貨幣監控與 Telegram 推播機器人的 Phase 1-3 基礎版本。

## 目前功能範圍

- `/start`、`/help`、`/price <symbol>`、`/fear` Telegram 指令
- `/setalert`、`/listalerts`、`/deletealert` 價格警報指令
- `/topgainers`、`/toplosers`、`/topvolume` 多幣種篩選指令
- `/subscribe`、`/unsubscribe`、`/subscriptions` 訂閱制指令
- `/chart <symbol>` 圖表輸出指令
- `/radar` 策略雷達推播摘要指令
- 使用 CoinGecko 免費 keyless API 查詢更完整的市場快照
- 使用 Binance Futures 公開市場資料取得 Funding / OI / Long-Short Ratio
- 整合 Alternative.me Fear & Greed 市場情緒指數
- 啟動通知與立即市場快報推播
- APScheduler 定期市場快報推播
- 使用 SQLite + SQLAlchemy 儲存 K 線資料
- 針對追蹤幣種同步 CoinGecko OHLC 歷史 K 線
- 內建 SMA、EMA、RSI、MACD 指標輔助函式
- 排程價格警報檢查，採一次性觸發後自動停用
- 使用者可自訂訂閱幣種，排程推播會依訂閱內容送出摘要
- 訂閱幣種支援事件型通知，例如急漲急跌、RSI 過熱過冷、MACD 交叉、OI 暗流、Funding 偏負
- 內建多幣種排行篩選、價格圖表輸出與策略雷達推播
- `.env` + `config.yaml` 設定載入
- `loguru` 日誌記錄

## 快速開始

1. 建立虛擬環境並安裝依賴。
2. 將 `.env.example` 複製為 `.env`，並填入 `TELEGRAM_BOT_TOKEN`。
3. 視需要更新 `config.yaml`。
4. 執行 `python -m bot.main`
5. 在 Telegram 測試 `/price BTC`、`/fear`、`/setalert BTC above 70000`、`/topgainers`、`/chart BTC`、`/radar`

## Phase 2 基礎功能

- 歷史 K 線會透過 `DATABASE_URL` 儲存在 SQLite
- 應用程式可為追蹤幣種同步 CoinGecko OHLC K 線
- 指標輔助函式目前位於 `analysis/indicators.py`
- `/price` 在有 K 線資料時可附帶 RSI 與 MACD 摘要
- 價格警報會儲存在 SQLite，並由排程定期檢查
- 多幣種篩選器會根據設定好的 screener 幣種清單產生排行
- 使用者訂閱資料會儲存在 SQLite，並影響定時摘要推播內容
- 圖表功能會輸出本地 PNG 檔，再由 Telegram 送出
- 歷史資料同步由 `config.yaml` 中的 `history` 區塊控制

## Phase 3 MVP：策略雷達

- 整合 CoinGecko trending 與市場快照
- 整合 Binance Futures 公開 Funding / Open Interest / Top Long-Short Ratio
- 產生熱度榜、追多榜、綜合榜、埋伏榜與值得關注摘要
- 可手動透過 `/radar` 查詢，也可透過排程主動推播

## `/price` 行為

- 接受 `BTC`、`btc`、`BTCUSDT`、`ETHUSD` 這類輸入
- 回覆價格、24h 漲跌、24h 區間、市值、成交量與資料時間
- 若本地已有歷史 K 線，或可即時補抓，會附上 RSI / MACD 摘要
- 不支援的幣種會回覆可用幣種提示，而不是通用 traceback

## 警報指令

- `/setalert BTC above 70000`
- `/setalert ETH below 3000`
- `/listalerts`
- `/deletealert 1`

## 多幣種篩選指令

- `/topgainers`
- `/toplosers`
- `/topvolume`

## 訂閱與圖表指令

- `/subscribe BTC`
- `/unsubscribe BTC`
- `/subscriptions`
- `/chart BTC`

## 事件型訂閱

- `/subscribe <symbol>` 之後，系統會定期檢查該幣種是否出現事件
- 目前事件包含：24h 急漲急跌、RSI 過熱/過冷、MACD 黃金/死亡交叉、OI 暗流、Funding 偏負
- 相同事件會套用 cooldown，避免短時間重複洗版
- 相關閾值與檢查頻率可在 `config.yaml` 的 `subscription_events` 區塊調整

## 雷達指令

- `/radar`

## 注意事項

- 若要使用排程推播，必須設定 `TELEGRAM_DEFAULT_CHAT_ID` 或 `push.chat_id`
- Scheduler 會隨 bot 進程一起啟動
- 啟動時 bot 會先送出上線通知與一則立即市場快報，之後才依照固定週期排程
- SQLite 執行期資料會存放在 `runtime/`，且已被 git 忽略
- 觸發過的警報為一次性警報，送出後會自動停用
- Matplotlib 設定快取會寫入 `runtime/mplconfig`，避免系統權限問題
- 策略雷達目前屬於規則引擎 MVP，分數與文字摘要可於後續再調參數
