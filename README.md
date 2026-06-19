# CryptoBot

CryptoBot 是一個加密貨幣監控與 Telegram 推播機器人的 Phase 1-3 基礎版本。

## 目前功能範圍

- `/start`、`/help`、`/price <symbol>`、`/fear` Telegram 指令
- `/setalert`、`/listalerts`、`/deletealert` 價格警報指令
- `/topgainers`、`/toplosers`、`/topvolume` 多幣種篩選指令
- `/subscribe`、`/unsubscribe`、`/subscriptions` 訂閱制指令
- `/chart <symbol>` 圖表輸出指令
- `/radar` 策略雷達推播摘要指令
- 使用 CoinGecko Demo / Pro API 查詢更完整的市場快照
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
- 若預設推播 chat 同時有使用 `/subscribe`，市場快報會自動合併預設幣種與訂閱幣種
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
- `/subscribe` 會先驗證是否為目前支援的 CoinGecko 幣種，避免寫入無法查價的訂閱
- 目前事件包含：24h 急漲急跌、RSI 過熱/過冷、MACD 黃金/死亡交叉、OI 暗流、Funding 偏負
- 相同事件會套用 cooldown，避免短時間重複洗版
- 相關閾值與檢查頻率可在 `config.yaml` 的 `subscription_events` 區塊調整
- 若當日截至上午或傍晚都沒有任何事件，可額外推送「今日無特殊事件」摘要

## 雷達指令

- `/radar`

## 注意事項

- 若要使用排程推播，必須設定 `TELEGRAM_DEFAULT_CHAT_ID` 或 `push.chat_id`
- CoinGecko 若使用付費 Pro key，請在 `.env` 設定 `COINGECKO_API_PLAN=pro`
- Scheduler 會隨 bot 進程一起啟動
- 啟動時 bot 會先送出上線通知與一則立即市場快報，之後才依照固定週期排程
- 目前雷達可設定固定時段推播，例如早 / 中 / 晚三個時段，且仍可手動使用 `/radar`
- SQLite 執行期資料會存放在 `runtime/`，且已被 git 忽略
- `WARNING` 與 `ERROR` 等級日誌會額外寫入 `runtime/logs/warnings-errors.log`
- 觸發過的警報為一次性警報，送出後會自動停用
- Matplotlib 設定快取會寫入 `runtime/mplconfig`，避免系統權限問題
- 策略雷達目前屬於規則引擎 MVP，分數與文字摘要可於後續再調參數

## 短線事件設定

- `subscription_events.price_change_threshold_pct` 控制 24h 急漲急跌事件
- `subscription_events.short_term_breakout_threshold_pct` 控制近幾根 K 線的短線突破 / 跌破事件
- `subscription_events.short_term_lookback_candles` 控制短線事件回看幾根 4h K 線
- `subscription_events.oi_surge_threshold_pct` 控制 OI 暗流事件門檻
- `subscription_events.funding_negative_threshold_pct` 控制 Funding 偏負事件門檻

## 疑難排解

- 若出現 Telegram `Conflict: terminated by other getUpdates request`，代表同一組 bot token 正在被另一個 polling 實例使用，請關閉其他本機程序、伺服器程序或 GitHub Actions job 後再啟動。
- 本專案啟動時會使用 `runtime/cryptobot.lock` 防止同一台機器重複啟動；若仍出現 Conflict，通常是另一台機器或雲端環境也在跑同一個 bot。
- CoinGecko 若使用 Demo key，請設定 `COINGECKO_API_PLAN=demo`；若使用 Pro key，請設定 `COINGECKO_API_PLAN=pro`，程式會自動切換 header 與 Pro base URL。
- CoinGecko 錯誤日誌只會記錄 symbol、coin id、plan、base URL 與狀態碼，不會輸出 API key。
