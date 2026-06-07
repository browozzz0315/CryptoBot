from __future__ import annotations

from time import perf_counter

from loguru import logger
from telegram.ext import Application, CommandHandler

from bot.formatters import format_startup_message
from bot.handlers.commands import fear_command, help_command, price_command, start_command
from data.coingecko import CoinGeckoClient
from data.fear_greed import FearGreedClient
from scheduler.jobs import push_market_summary, sync_market_history
from scheduler.runner import configure_scheduler
from storage.candles import CandleRepository
from storage.database import create_engine, create_session_factory, init_database
from utils.config_loader import load_settings
from utils.logger import setup_logger


async def post_init(application: Application) -> None:
    settings = application.bot_data["settings"]
    await init_database(application.bot_data["db_engine"])
    scheduler = configure_scheduler(application, settings)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler

    startup_elapsed = perf_counter() - application.bot_data["startup_started_at"]
    logger.info("Telegram bot startup completed in {:.2f}s", startup_elapsed)

    if settings.push.chat_id:
        await application.bot.send_message(
            chat_id=settings.push.chat_id,
            text=format_startup_message(
                tracked_symbols=settings.market.tracked_symbols,
                interval_minutes=settings.push.interval_minutes,
            ),
        )
        try:
            await push_market_summary(application)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send initial market summary during startup")

    if settings.history.enabled and settings.history.sync_on_startup:
        try:
            await sync_market_history(application)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to sync market history during startup")


async def post_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)

    coingecko_client = application.bot_data.get("coingecko_client")
    if coingecko_client:
        await coingecko_client.aclose()

    fear_greed_client = application.bot_data.get("fear_greed_client")
    if fear_greed_client:
        await fear_greed_client.aclose()

    db_engine = application.bot_data.get("db_engine")
    if db_engine:
        await db_engine.dispose()


def build_application() -> Application:
    settings = load_settings()
    setup_logger(settings.app.log_level)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.bot_data["settings"] = settings
    application.bot_data["startup_started_at"] = perf_counter()
    application.bot_data["db_engine"] = create_engine(settings.storage.database_url)
    application.bot_data["db_session_factory"] = create_session_factory(
        application.bot_data["db_engine"]
    )
    application.bot_data["candle_repository"] = CandleRepository(
        application.bot_data["db_session_factory"]
    )
    application.bot_data["coingecko_client"] = CoinGeckoClient(
        base_url=settings.api.coingecko.base_url,
        api_key=settings.coingecko_api_key,
        quote_currency=settings.market.quote_currency,
    )
    application.bot_data["fear_greed_client"] = FearGreedClient(
        base_url=settings.api.fear_greed.base_url,
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("fear", fear_command))
    return application


def main() -> None:
    application = build_application()
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
