from __future__ import annotations

from telegram.ext import Application, CommandHandler

from bot.handlers.commands import help_command, price_command, start_command
from data.coingecko import CoinGeckoClient
from scheduler.runner import configure_scheduler
from utils.config_loader import load_settings
from utils.logger import setup_logger


async def post_init(application: Application) -> None:
    settings = application.bot_data["settings"]
    scheduler = configure_scheduler(application, settings)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler


async def post_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)

    coingecko_client = application.bot_data.get("coingecko_client")
    if coingecko_client:
        await coingecko_client.aclose()


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
    application.bot_data["coingecko_client"] = CoinGeckoClient(
        base_url=settings.api.coingecko.base_url,
        api_key=settings.coingecko_api_key,
        quote_currency=settings.market.quote_currency,
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    return application


def main() -> None:
    application = build_application()
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
