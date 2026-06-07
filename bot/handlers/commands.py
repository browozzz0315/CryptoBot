from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from bot.formatters import format_fear_greed_message, format_price_message
from loguru import logger


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "CryptoBot 已啟動。\n"
        "可用指令：\n"
        "/help - 查看指令說明\n"
        "/price BTC - 查詢幣價\n"
        "/fear - 查詢市場情緒"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - 初始化機器人\n"
        "/help - 顯示說明\n"
        "/price <symbol> - 查詢指定幣種即時價格\n"
        "/fear - 查詢 Fear & Greed 市場情緒"
    )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    coingecko_client = context.application.bot_data["coingecko_client"]
    fear_greed_client = context.application.bot_data["fear_greed_client"]

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
