from __future__ import annotations

from datetime import datetime

from loguru import logger
from telegram.ext import Application

from bot.formatters import format_market_summary
from storage.candles import CandleRecord


async def push_market_summary(application: Application) -> None:
    settings = application.bot_data["settings"]
    coingecko_client = application.bot_data["coingecko_client"]
    fear_greed_client = application.bot_data["fear_greed_client"]

    chat_id = settings.push.chat_id
    if not chat_id:
        logger.warning("Scheduled push skipped because chat_id is not configured.")
        return

    symbols = settings.market.tracked_symbols
    quotes = await coingecko_client.get_prices(symbols)
    message = format_market_summary(quotes, datetime.now())

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch Fear & Greed index for scheduled push")
    else:
        message = (
            f"{message}\n\n"
            f"😱 Fear & Greed：{sentiment['value']}（{sentiment['classification']}）"
        )

    await application.bot.send_message(chat_id=chat_id, text=message)


async def sync_market_history(application: Application) -> None:
    settings = application.bot_data["settings"]
    coingecko_client = application.bot_data["coingecko_client"]
    candle_repository = application.bot_data["candle_repository"]

    if not settings.history.enabled:
        logger.info("History sync skipped because it is disabled in config.")
        return

    total_written = 0
    for symbol in settings.market.tracked_symbols:
        candle_rows = await coingecko_client.get_ohlc(symbol, settings.history.ohlc_days)
        records = [
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
        total_written += await candle_repository.upsert_candles(records)

    logger.info("History sync completed. Upserted {} candle rows.", total_written)
