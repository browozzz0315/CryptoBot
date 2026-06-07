from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from analysis.signals import build_indicator_snapshot
from bot.formatters import (
    format_alert_created_message,
    format_alert_list_message,
    format_fear_greed_message,
    format_price_message,
)
from loguru import logger
from storage.candles import CandleRecord
from storage.alerts import PriceAlertRecord


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "CryptoBot 已啟動。\n"
        "可用指令：\n"
        "/help - 查看指令說明\n"
        "/price BTC - 查詢幣價\n"
        "/fear - 查詢市場情緒\n"
        "/setalert BTC above 70000 - 建立價格警報\n"
        "/listalerts - 查看警報\n"
        "/deletealert 1 - 刪除警報"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - 初始化機器人\n"
        "/help - 顯示說明\n"
        "/price <symbol> - 查詢指定幣種即時價格\n"
        "/fear - 查詢 Fear & Greed 市場情緒\n"
        "/setalert <symbol> <above|below> <price> - 建立警報\n"
        "/listalerts - 查看啟用中的警報\n"
        "/deletealert <id> - 刪除指定警報"
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
