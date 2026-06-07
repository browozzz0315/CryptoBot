from __future__ import annotations

from datetime import datetime

from loguru import logger
from telegram.ext import Application

from analysis.radar import (
    RadarEntry,
    build_ambush_rank,
    build_composite_rank,
    build_heat_rank,
    build_highlights,
    build_long_rank,
    calculate_oi_change_pct,
    estimate_sideways_days,
)
from bot.formatters import format_market_summary
from bot.formatters import format_alert_triggered_message
from bot.formatters import format_radar_message
from storage.candles import CandleRecord


async def push_market_summary(application: Application) -> None:
    settings = application.bot_data["settings"]
    coingecko_client = application.bot_data["coingecko_client"]
    fear_greed_client = application.bot_data["fear_greed_client"]
    user_subscription_repository = application.bot_data["user_subscription_repository"]

    chat_id = settings.push.chat_id
    symbols = settings.market.tracked_symbols
    quotes = await coingecko_client.get_prices(symbols)
    message = format_market_summary(quotes, datetime.now())
    sentiment_message = None

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch Fear & Greed index for scheduled push")
    else:
        sentiment_message = f"😱 Fear & Greed：{sentiment['value']}（{sentiment['classification']}）"
        message = f"{message}\n\n{sentiment_message}"

    if chat_id:
        await application.bot.send_message(chat_id=chat_id, text=message)
    else:
        logger.warning("Default scheduled push skipped because chat_id is not configured.")

    # Send user-specific summaries based on their subscriptions.
    delivered_chat_ids = {str(chat_id)} if chat_id else set()
    subscriptions = await _load_subscription_map(user_subscription_repository)
    for subscribed_chat_id, subscribed_symbols in subscriptions.items():
        if subscribed_chat_id in delivered_chat_ids:
            continue
        subscription_quotes = await coingecko_client.get_prices(subscribed_symbols)
        subscription_message = format_market_summary(subscription_quotes, datetime.now())
        if sentiment_message:
            subscription_message = f"{subscription_message}\n\n{sentiment_message}"
        await application.bot.send_message(chat_id=subscribed_chat_id, text=subscription_message)


async def sync_market_history(application: Application) -> None:
    settings = application.bot_data["settings"]
    coingecko_client = application.bot_data["coingecko_client"]
    candle_repository = application.bot_data["candle_repository"]

    if not settings.history.enabled:
        logger.info("History sync skipped because it is disabled in config.")
        return

    total_written = 0
    symbols_to_sync = set(settings.market.tracked_symbols)
    if settings.screener.enabled:
        symbols_to_sync.update(settings.screener.symbols)
    if settings.radar.enabled:
        symbols_to_sync.update(settings.radar.symbols)

    for symbol in sorted(symbols_to_sync):
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


async def check_price_alerts(application: Application) -> None:
    settings = application.bot_data["settings"]
    if not settings.alerts.enabled:
        return

    alert_repository = application.bot_data["alert_repository"]
    coingecko_client = application.bot_data["coingecko_client"]
    active_alerts = await alert_repository.list_active_alerts()
    if not active_alerts:
        return

    symbol_quotes: dict[str, dict[str, float | str | datetime]] = {}
    for alert in active_alerts:
        symbol = alert.symbol.upper()
        if symbol not in symbol_quotes:
            try:
                symbol_quotes[symbol] = await coingecko_client.get_price(symbol)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to fetch price while evaluating alerts for {}", symbol)
                continue

        quote = symbol_quotes[symbol]
        current_price = float(quote["price"])
        should_trigger = (
            alert.direction == "above" and current_price >= alert.target_price
        ) or (
            alert.direction == "below" and current_price <= alert.target_price
        )
        if not should_trigger:
            continue

        await application.bot.send_message(
            chat_id=alert.chat_id,
            text=format_alert_triggered_message(
                symbol=symbol,
                direction=alert.direction,
                target_price=alert.target_price,
                current_price=current_price,
            ),
        )
        await alert_repository.mark_triggered(alert.id)


async def _load_subscription_map(user_subscription_repository) -> dict[str, list[str]]:
    subscriptions = await user_subscription_repository.list_all_subscriptions()
    grouped: dict[str, list[str]] = {}
    for subscription in subscriptions:
        grouped.setdefault(subscription.chat_id, []).append(subscription.symbol)
    return grouped


async def push_strategy_radar(application: Application, *, deliver: bool = True) -> str:
    settings = application.bot_data["settings"]
    if not settings.radar.enabled:
        raise ValueError("雷達功能已停用。")

    coingecko_client = application.bot_data["coingecko_client"]
    binance_futures_client = application.bot_data["binance_futures_client"]
    candle_repository = application.bot_data["candle_repository"]

    quotes = await coingecko_client.get_prices(settings.radar.symbols)
    try:
        trending_symbols = set(await coingecko_client.get_trending_symbols())
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch CoinGecko trending symbols for radar")
        trending_symbols = set()

    entries: list[RadarEntry] = []
    for quote in quotes:
        symbol = str(quote["symbol"])
        funding_rate = None
        oi_change_pct = None
        long_short_ratio = None

        try:
            funding = await binance_futures_client.get_latest_funding_rate(symbol)
            funding_rate = float(funding["funding_rate"]) * 100
        except Exception:  # noqa: BLE001
            logger.warning("Radar funding data unavailable for {}", symbol)

        try:
            oi_hist = await binance_futures_client.get_open_interest_hist(symbol, period="1d", limit=2)
            oi_values = [float(item["open_interest_value"]) for item in oi_hist]
            oi_change_pct = calculate_oi_change_pct(oi_values)
        except Exception:  # noqa: BLE001
            logger.warning("Radar OI data unavailable for {}", symbol)

        try:
            ratio = await binance_futures_client.get_top_long_short_ratio(symbol, period="1d", limit=1)
            long_short_ratio = float(ratio["long_short_ratio"])
        except Exception:  # noqa: BLE001
            logger.warning("Radar long/short ratio unavailable for {}", symbol)

        close_prices = await candle_repository.list_close_prices(
            symbol=symbol,
            timeframe="4h",
            source="coingecko",
            limit=settings.radar.sideways_lookback_candles,
        )
        if not close_prices and settings.history.enabled:
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
            close_prices = await candle_repository.list_close_prices(
                symbol=symbol,
                timeframe="4h",
                source="coingecko",
                limit=settings.radar.sideways_lookback_candles,
            )

        sideways_days = estimate_sideways_days(
            close_prices,
            threshold_pct=settings.radar.sideways_threshold_pct,
        )

        entries.append(
            RadarEntry(
                symbol=symbol,
                market_cap=float(quote["market_cap"]),
                change_24h=float(quote["change_24h"]),
                total_volume=float(quote["total_volume"]),
                funding_rate=funding_rate,
                oi_change_pct=oi_change_pct,
                long_short_ratio=long_short_ratio,
                sideways_days=sideways_days,
                trending=symbol in trending_symbols,
            )
        )

    heat_entries = build_heat_rank(entries, settings.radar.heat_top_n)
    long_entries = build_long_rank(entries, settings.radar.long_top_n)
    composite_entries = build_composite_rank(entries, settings.radar.composite_top_n)
    ambush_entries = build_ambush_rank(entries, settings.radar.ambush_top_n)
    highlights = build_highlights(
        heat_entries=heat_entries,
        long_entries=long_entries,
        composite_entries=composite_entries,
        ambush_entries=ambush_entries,
    )

    message = format_radar_message(
        timestamp=datetime.utcnow(),
        heat_entries=heat_entries,
        long_entries=long_entries,
        composite_entries=composite_entries,
        ambush_entries=ambush_entries,
        highlights=highlights,
    )

    if deliver and settings.push.chat_id and settings.radar.schedule_enabled:
        await application.bot.send_message(chat_id=settings.push.chat_id, text=message)

    return message
