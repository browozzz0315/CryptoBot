from __future__ import annotations

from datetime import datetime

from loguru import logger
from telegram.ext import Application

from bot.formatters import format_market_summary


async def push_market_summary(application: Application) -> None:
    settings = application.bot_data["settings"]
    coingecko_client = application.bot_data["coingecko_client"]

    chat_id = settings.push.chat_id
    if not chat_id:
        logger.warning("Scheduled push skipped because chat_id is not configured.")
        return

    symbols = settings.market.tracked_symbols
    quotes = await coingecko_client.get_prices(symbols)
    message = format_market_summary(quotes, datetime.now())
    await application.bot.send_message(chat_id=chat_id, text=message)
