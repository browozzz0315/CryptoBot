from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.formatters import format_price_message
from loguru import logger


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "CryptoBot 已啟動。\n"
        "可用指令：\n"
        "/help - 查看指令說明\n"
        "/price BTC - 查詢幣價"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - 初始化機器人\n"
        "/help - 顯示說明\n"
        "/price <symbol> - 查詢指定幣種即時價格"
    )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    coingecko_client = context.application.bot_data["coingecko_client"]

    symbol = (
        context.args[0].upper()
        if context.args
        else settings.market.default_price_symbol.upper()
    )

    try:
        quote = await coingecko_client.get_price(symbol)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch price for {}", symbol)
        await update.message.reply_text(f"查詢 {symbol} 價格失敗：{exc}")
        return

    await update.message.reply_text(
        format_price_message(symbol, quote["price"], quote["change_24h"])
    )
