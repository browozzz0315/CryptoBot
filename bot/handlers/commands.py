from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from analysis.screener import top_gainers, top_losers, top_volume
from analysis.signals import build_indicator_snapshot
from bot.formatters import (
    format_alert_created_message,
    format_alert_list_message,
    format_fear_greed_message,
    format_price_message,
    format_screener_message,
    format_subscription_message,
)
from charts.candlestick import render_price_chart
from loguru import logger
from scheduler.jobs import push_strategy_radar
from storage.candles import CandleRecord
from storage.alerts import PriceAlertRecord
from storage.users import UserSubscriptionRecord


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "CryptoBot 已啟動。\n"
        "可用指令：\n"
        "/help - 查看指令說明\n"
        "/price BTC - 查詢幣價\n"
        "/fear - 查詢市場情緒\n"
        "/setalert BTC above 70000 - 建立價格警報\n"
        "/listalerts - 查看警報\n"
        "/deletealert 1 - 刪除警報\n"
        "/topgainers - 看漲幅排行\n"
        "/toplosers - 看跌幅排行\n"
        "/topvolume - 看成交量排行\n"
        "/subscribe BTC - 訂閱幣種與事件通知\n"
        "/unsubscribe BTC - 取消訂閱\n"
        "/subscriptions - 查看訂閱\n"
        "/chart BTC - 取得圖表\n"
        "/radar - 取得策略雷達推播"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - 初始化機器人\n"
        "/help - 顯示說明\n"
        "/price <symbol> - 查詢指定幣種即時價格\n"
        "/fear - 查詢 Fear & Greed 市場情緒\n"
        "/setalert <symbol> <above|below> <price> - 建立警報\n"
        "/listalerts - 查看啟用中的警報\n"
        "/deletealert <id> - 刪除指定警報\n"
        "/topgainers - 查看漲幅排行\n"
        "/toplosers - 查看跌幅排行\n"
        "/topvolume - 查看成交量排行\n"
        "/subscribe <symbol> - 訂閱幣種與事件通知\n"
        "/unsubscribe <symbol> - 取消訂閱幣種\n"
        "/subscriptions - 查看已訂閱幣種\n"
        "/chart <symbol> - 產生價格圖表\n"
        "/radar - 產生策略雷達摘要"
    )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    coingecko_client = context.application.bot_data["coingecko_client"]
    fear_greed_client = context.application.bot_data["fear_greed_client"]
    candle_repository = context.application.bot_data["candle_repository"]

    raw_symbol = (
        context.args[0]
        if context.args
        else settings.market.default_price_symbol
    )

    try:
        quote = await coingecko_client.get_price(raw_symbol)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch price for {}", raw_symbol)
        await update.message.reply_text(f"查詢 {raw_symbol.upper()} 價格失敗：{exc}")
        return

    indicators = None
    try:
        close_prices = await candle_repository.list_close_prices(
            symbol=str(quote["symbol"]),
            timeframe="4h",
            source="coingecko",
            limit=60,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to load candle history for {}", quote["symbol"])
    else:
        if not close_prices and settings.history.enabled:
            try:
                candle_rows = await coingecko_client.get_ohlc(
                    str(quote["symbol"]),
                    settings.history.ohlc_days,
                )
                await candle_repository.upsert_candles(
                    [
                        CandleRecord(
                            symbol=str(row["symbol"]),
                            timeframe=str(row["timeframe"]),
                            source=str(row["source"]),
                            open_time=row["open_time"],
                            close_time=row["close_time"],
                            open_price=float(row["open_price"]),
                            high_price=float(row["high_price"]),
                            low_price=float(row["low_price"]),
                            close_price=float(row["close_price"]),
                        )
                        for row in candle_rows
                    ]
                )
                close_prices = await candle_repository.list_close_prices(
                    symbol=str(quote["symbol"]),
                    timeframe="4h",
                    source="coingecko",
                    limit=60,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to backfill candle history for {}", quote["symbol"])

        if close_prices:
            indicators = build_indicator_snapshot(close_prices)

    message = format_price_message(
        symbol=str(quote["symbol"]),
        name=str(quote["name"]),
        price=float(quote["price"]),
        change_24h=float(quote["change_24h"]),
        quote_currency=settings.market.quote_currency,
        market_cap=float(quote["market_cap"]),
        total_volume=float(quote["total_volume"]),
        high_24h=float(quote["high_24h"]),
        low_24h=float(quote["low_24h"]),
        updated_at=quote["last_updated_at"],
        indicators=indicators,
    )

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch Fear & Greed index for /price response")
    else:
        message = (
            f"{message}\n\n"
            f"😱 市場情緒：{sentiment['value']}（{sentiment['classification']}）"
        )

    await update.message.reply_text(message)


async def fear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fear_greed_client = context.application.bot_data["fear_greed_client"]

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch Fear & Greed index")
        await update.message.reply_text(f"查詢 Fear & Greed 失敗：{exc}")
        return

    await update.message.reply_text(
        format_fear_greed_message(
            value=sentiment["value"],
            classification=sentiment["classification"],
            updated_at=sentiment["updated_at"],
        )
    )


async def set_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 3:
        await update.message.reply_text("用法：/setalert <symbol> <above|below> <price>")
        return

    raw_symbol, direction, raw_price = context.args
    direction = direction.lower()
    if direction not in {"above", "below"}:
        await update.message.reply_text("方向只接受 above 或 below。")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    alert_repository = context.application.bot_data["alert_repository"]

    try:
        symbol = coingecko_client.normalize_symbol(raw_symbol)
        target_price = float(raw_price)
    except ValueError as exc:
        await update.message.reply_text(f"警報建立失敗：{exc}")
        return

    if target_price <= 0:
        await update.message.reply_text("價格門檻必須大於 0。")
        return

    chat = update.effective_chat
    if chat is None:
        await update.message.reply_text("找不到 chat 資訊，無法建立警報。")
        return

    alert = await alert_repository.create_alert(
        PriceAlertRecord(
            chat_id=str(chat.id),
            symbol=symbol,
            direction=direction,
            target_price=target_price,
        )
    )

    await update.message.reply_text(
        format_alert_created_message(alert.id, alert.symbol, alert.direction, alert.target_price)
    )


async def list_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alert_repository = context.application.bot_data["alert_repository"]
    chat = update.effective_chat
    if chat is None:
        await update.message.reply_text("找不到 chat 資訊。")
        return

    alerts = await alert_repository.list_alerts(chat_id=str(chat.id))
    await update.message.reply_text(
        format_alert_list_message(
            [
                {
                    "id": alert.id,
                    "symbol": alert.symbol,
                    "direction": alert.direction,
                    "target_price": alert.target_price,
                }
                for alert in alerts
            ]
        )
    )


async def delete_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("用法：/deletealert <id>")
        return

    try:
        alert_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("警報 ID 必須是整數。")
        return

    alert_repository = context.application.bot_data["alert_repository"]
    chat = update.effective_chat
    if chat is None:
        await update.message.reply_text("找不到 chat 資訊。")
        return

    deleted = await alert_repository.delete_alert(chat_id=str(chat.id), alert_id=alert_id)
    if not deleted:
        await update.message.reply_text(f"找不到啟用中的警報 #{alert_id}。")
        return

    await update.message.reply_text(f"🗑️ 已刪除警報 #{alert_id}")


async def top_gainers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screener_result(update, context, mode="gainers")


async def top_losers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screener_result(update, context, mode="losers")


async def top_volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screener_result(update, context, mode="volume")


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("用法：/subscribe <symbol>")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    chat = update.effective_chat
    if chat is None:
        await update.message.reply_text("找不到 chat 資訊。")
        return

    try:
        symbol = coingecko_client.normalize_symbol(context.args[0])
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    await user_subscription_repository.upsert_subscription(
        UserSubscriptionRecord(
            chat_id=str(chat.id),
            symbol=symbol,
        )
    )
    await update.message.reply_text(
        f"✅ 已訂閱 {symbol}\n"
        "之後你會收到：\n"
        "1. 固定摘要中的訂閱幣種內容\n"
        "2. 該幣種的事件型通知，例如急漲急跌、RSI 過熱過冷、MACD 交叉、OI 暗流、Funding 偏負"
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("用法：/unsubscribe <symbol>")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    chat = update.effective_chat
    if chat is None:
        await update.message.reply_text("找不到 chat 資訊。")
        return

    try:
        symbol = coingecko_client.normalize_symbol(context.args[0])
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    deleted = await user_subscription_repository.delete_subscription(
        chat_id=str(chat.id),
        symbol=symbol,
    )
    if not deleted:
        await update.message.reply_text(f"目前沒有訂閱 {symbol}")
        return

    await update.message.reply_text(f"🗑️ 已取消訂閱 {symbol}")


async def subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    chat = update.effective_chat
    if chat is None:
        await update.message.reply_text("找不到 chat 資訊。")
        return

    subscriptions = await user_subscription_repository.list_subscriptions(chat_id=str(chat.id))
    await update.message.reply_text(
        format_subscription_message([subscription.symbol for subscription in subscriptions])
    )


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    coingecko_client = context.application.bot_data["coingecko_client"]
    candle_repository = context.application.bot_data["candle_repository"]

    raw_symbol = context.args[0] if context.args else settings.market.default_price_symbol
    try:
        symbol = coingecko_client.normalize_symbol(raw_symbol)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    candles = await candle_repository.list_candles(
        symbol=symbol,
        timeframe="4h",
        source="coingecko",
        limit=settings.charts.default_limit,
    )
    if not candles and settings.history.enabled:
        candle_rows = await coingecko_client.get_ohlc(symbol, settings.history.ohlc_days)
        await candle_repository.upsert_candles(
            [
                CandleRecord(
                    symbol=str(row["symbol"]),
                    timeframe=str(row["timeframe"]),
                    source=str(row["source"]),
                    open_time=row["open_time"],
                    close_time=row["close_time"],
                    open_price=float(row["open_price"]),
                    high_price=float(row["high_price"]),
                    low_price=float(row["low_price"]),
                    close_price=float(row["close_price"]),
                )
                for row in candle_rows
            ]
        )
        candles = await candle_repository.list_candles(
            symbol=symbol,
            timeframe="4h",
            source="coingecko",
            limit=settings.charts.default_limit,
        )

    if not candles:
        await update.message.reply_text("目前沒有可用的圖表資料。")
        return

    chart_path = render_price_chart(symbol=symbol, candles=candles, output_dir=settings.charts.output_dir)
    with chart_path.open("rb") as photo:
        await update.message.reply_photo(photo=photo, caption=f"{symbol} 價格圖表")


async def _send_screener_result(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    settings = context.application.bot_data["settings"]
    if not settings.screener.enabled:
        await update.message.reply_text("Screener 功能目前已停用。")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    quotes = await coingecko_client.get_prices(settings.screener.symbols)

    if mode == "gainers":
        title = "🚀 24h 漲幅排行"
        ranked = top_gainers(quotes, settings.screener.top_n)
    elif mode == "losers":
        title = "📉 24h 跌幅排行"
        ranked = top_losers(quotes, settings.screener.top_n)
    else:
        title = "💧 24h 成交量排行"
        ranked = top_volume(quotes, settings.screener.top_n)

    await update.message.reply_text(format_screener_message(title, ranked))


async def radar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = await push_strategy_radar(context.application, deliver=False)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to generate strategy radar")
        await update.message.reply_text(f"產生策略雷達失敗：{exc}")
        return

    await update.message.reply_text(message)
