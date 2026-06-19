from __future__ import annotations

from time import perf_counter

from loguru import logger
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.formatters import format_startup_message
from bot.handlers.commands import (
    chart_command,
    delete_alert_command,
    events_command,
    fear_command,
    help_command,
    list_alerts_command,
    price_command,
    radar_command,
    subscribe_command,
    subscriptions_command,
    set_alert_command,
    start_command,
    status_command,
    top_gainers_command,
    top_losers_command,
    top_volume_command,
    unsubscribe_command,
)
from data.binance_futures import BinanceFuturesClient
from data.coingecko import CoinGeckoClient
from data.fear_greed import FearGreedClient
from scheduler.jobs import push_market_summary, sync_market_history
from scheduler.runner import configure_scheduler
from storage.alerts import AlertRepository
from storage.candles import CandleRepository
from storage.database import create_engine, create_session_factory, init_database
from storage.subscription_events import SubscriptionEventStateRepository
from storage.users import UserSubscriptionRepository
from utils.config_loader import load_settings
from utils.logger import setup_logger
from utils.single_instance import AlreadyRunningError, SingleInstanceLock


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

    binance_futures_client = application.bot_data.get("binance_futures_client")
    if binance_futures_client:
        await binance_futures_client.aclose()

    db_engine = application.bot_data.get("db_engine")
    if db_engine:
        await db_engine.dispose()

    single_instance_lock = application.bot_data.get("single_instance_lock")
    if single_instance_lock:
        single_instance_lock.release()


async def telegram_error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if isinstance(context.error, Conflict):
        logger.error(
            "Telegram polling conflict detected. "
            "Only one bot instance can call getUpdates for the same token. "
            "Stop the other local process, GitHub Action, server, or webhook/polling instance."
        )
        return

    logger.opt(exception=context.error).error("Unhandled Telegram bot error. update={}", update)


def build_application() -> Application:
    settings = load_settings()
    setup_logger(settings.app.log_level)
    coingecko_base_url = (
        "https://pro-api.coingecko.com/api/v3"
        if settings.coingecko_api_plan == "pro"
        else settings.api.coingecko.base_url
    )

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
    application.bot_data["alert_repository"] = AlertRepository(
        application.bot_data["db_session_factory"]
    )
    application.bot_data["user_subscription_repository"] = UserSubscriptionRepository(
        application.bot_data["db_session_factory"]
    )
    application.bot_data["subscription_event_state_repository"] = SubscriptionEventStateRepository(
        application.bot_data["db_session_factory"]
    )
    application.bot_data["coingecko_client"] = CoinGeckoClient(
        base_url=coingecko_base_url,
        api_key=settings.coingecko_api_key,
        api_plan=settings.coingecko_api_plan,
        quote_currency=settings.market.quote_currency,
    )
    application.bot_data["binance_futures_client"] = BinanceFuturesClient(
        base_url=settings.api.binance_futures.base_url,
    )
    application.bot_data["fear_greed_client"] = FearGreedClient(
        base_url=settings.api.fear_greed.base_url,
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("fear", fear_command))
    application.add_handler(CommandHandler("setalert", set_alert_command))
    application.add_handler(CommandHandler("listalerts", list_alerts_command))
    application.add_handler(CommandHandler("deletealert", delete_alert_command))
    application.add_handler(CommandHandler("topgainers", top_gainers_command))
    application.add_handler(CommandHandler("toplosers", top_losers_command))
    application.add_handler(CommandHandler("topvolume", top_volume_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("subscriptions", subscriptions_command))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(CommandHandler("radar", radar_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("diag", status_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_error_handler(telegram_error_handler)
    return application


def main() -> None:
    single_instance_lock = SingleInstanceLock("runtime/cryptobot.lock")
    try:
        single_instance_lock.acquire()
    except AlreadyRunningError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    try:
        application = build_application()
        application.bot_data["single_instance_lock"] = single_instance_lock
        application.run_polling(allowed_updates=None)
    finally:
        single_instance_lock.release()


if __name__ == "__main__":
    main()
