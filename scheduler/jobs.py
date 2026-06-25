from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from telegram.ext import Application

from analysis.radar import (
    RadarEntry,
    build_ambush_rank,
    build_composite_rank,
    build_dynamic_candidate_quotes,
    build_heat_rank,
    build_liquid_mid_cap_rank,
    build_highlights,
    build_long_rank,
    build_mainstream_rank,
    build_mover_rank,
    calculate_oi_change_pct,
    estimate_sideways_days,
)
from analysis.signals import detect_subscription_events, should_push_event
from bot.formatters import format_market_summary
from bot.formatters import format_alert_triggered_message
from bot.formatters import format_radar_message
from bot.formatters import format_subscription_event_message
from storage.candles import CandleRecord
from storage.subscription_events import SubscriptionEventStateRecord
from utils.logger import log_external_data_error


async def push_market_summary(application: Application) -> None:
    settings = application.bot_data["settings"]
    coingecko_client = application.bot_data["coingecko_client"]
    fear_greed_client = application.bot_data["fear_greed_client"]
    user_subscription_repository = application.bot_data["user_subscription_repository"]

    chat_id = settings.push.chat_id
    subscriptions = await _load_subscription_map(user_subscription_repository)
    sentiment_message = None

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception as exc:  # noqa: BLE001
        log_external_data_error("Failed to fetch Fear & Greed index for scheduled push", exc)
    else:
        sentiment_message = f"😱 Fear & Greed：{sentiment['value']}（{sentiment['classification']}）"

    if chat_id:
        summary_symbols = _resolve_summary_symbols(
            default_symbols=settings.market.tracked_symbols,
            subscribed_symbols=subscriptions.get(str(chat_id), []),
            coingecko_client=coingecko_client,
            context_label=f"default summary chat {chat_id}",
        )
        quotes = await coingecko_client.get_prices(summary_symbols)
        message = format_market_summary(quotes, datetime.now())
        if sentiment_message:
            message = f"{message}\n\n{sentiment_message}"
        await application.bot.send_message(chat_id=chat_id, text=message)
    else:
        logger.warning("Default scheduled push skipped because chat_id is not configured.")

    # Send user-specific summaries based on their subscriptions.
    delivered_chat_ids = {str(chat_id)} if chat_id else set()
    for subscribed_chat_id, subscribed_symbols in subscriptions.items():
        if subscribed_chat_id in delivered_chat_ids:
            continue
        summary_symbols = _resolve_summary_symbols(
            default_symbols=[],
            subscribed_symbols=subscribed_symbols,
            coingecko_client=coingecko_client,
            context_label=f"scheduled summary chat {subscribed_chat_id}",
        )
        if not summary_symbols:
            continue
        subscription_quotes = await coingecko_client.get_prices(summary_symbols)
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
            except Exception as exc:  # noqa: BLE001
                log_external_data_error("Failed to fetch price while evaluating alerts for {}", exc, symbol)
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


async def check_subscription_events(application: Application) -> None:
    settings = application.bot_data["settings"]
    if not settings.subscription_events.enabled:
        return

    user_subscription_repository = application.bot_data["user_subscription_repository"]
    subscription_event_state_repository = application.bot_data["subscription_event_state_repository"]
    coingecko_client = application.bot_data["coingecko_client"]
    binance_futures_client = application.bot_data["binance_futures_client"]
    candle_repository = application.bot_data["candle_repository"]

    subscriptions = await _load_subscription_map(user_subscription_repository)
    if not subscriptions:
        return

    unique_symbols = sorted(
        {
            symbol
            for symbols in subscriptions.values()
            for symbol in _filter_supported_symbols(
                coingecko_client=coingecko_client,
                symbols=symbols,
                context_label="subscription event check",
            )
        }
    )
    now = datetime.now(tz=UTC)
    quote_cache: dict[str, dict[str, float | str | datetime]] = {}
    close_price_cache: dict[str, list[float]] = {}
    derivatives_cache: dict[str, tuple[float | None, float | None]] = {}
    short_term_change_cache: dict[str, float | None] = {}

    for symbol in unique_symbols:
        try:
            quote_cache[symbol] = await coingecko_client.get_price(symbol)
        except Exception as exc:  # noqa: BLE001
            log_external_data_error("Failed to fetch quote for subscription event check: {}", exc, symbol)
            continue

        try:
            close_prices = await candle_repository.list_close_prices(
                symbol=symbol,
                timeframe="4h",
                source="coingecko",
                limit=settings.subscription_events.history_limit,
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
                    limit=settings.subscription_events.history_limit,
                )
            close_price_cache[symbol] = close_prices
            short_term_change_cache[symbol] = _calculate_short_term_change_pct(
                close_prices,
                lookback_candles=settings.subscription_events.short_term_lookback_candles,
            )
        except Exception as exc:  # noqa: BLE001
            log_external_data_error("Failed to load close prices for subscription event check: {}", exc, symbol)
            close_price_cache[symbol] = []
            short_term_change_cache[symbol] = None

        funding_rate = None
        oi_change_pct = None
        try:
            funding = await binance_futures_client.get_latest_funding_rate(symbol)
            funding_rate = float(funding["funding_rate"]) * 100
        except Exception:  # noqa: BLE001
            logger.warning("Subscription event funding data unavailable for {}", symbol)

        try:
            oi_hist = await binance_futures_client.get_open_interest_hist(symbol, period="1d", limit=2)
            oi_values = [float(item["open_interest_value"]) for item in oi_hist]
            oi_change_pct = calculate_oi_change_pct(oi_values)
        except Exception:  # noqa: BLE001
            logger.warning("Subscription event OI data unavailable for {}", symbol)

        derivatives_cache[symbol] = (funding_rate, oi_change_pct)

    for chat_id, symbols in subscriptions.items():
        for symbol in symbols:
            quote = quote_cache.get(symbol)
            if quote is None:
                continue

            close_prices = close_price_cache.get(symbol, [])
            funding_rate, oi_change_pct = derivatives_cache.get(symbol, (None, None))
            events = detect_subscription_events(
                symbol=symbol,
                close_prices=close_prices,
                change_24h=float(quote["change_24h"]),
                short_term_change_pct=short_term_change_cache.get(symbol),
                funding_rate=funding_rate,
                oi_change_pct=oi_change_pct,
                price_change_threshold_pct=settings.subscription_events.price_change_threshold_pct,
                short_term_breakout_threshold_pct=settings.subscription_events.short_term_breakout_threshold_pct,
                rsi_overbought=settings.subscription_events.rsi_overbought,
                rsi_oversold=settings.subscription_events.rsi_oversold,
                oi_surge_threshold_pct=settings.subscription_events.oi_surge_threshold_pct,
                price_flat_threshold_pct=settings.subscription_events.price_flat_threshold_pct,
                funding_negative_threshold_pct=settings.subscription_events.funding_negative_threshold_pct,
                min_confirmations=settings.subscription_events.min_confirmations,
            )
            if not events:
                continue

            event_lines: list[str] = []
            for event in events:
                if not should_push_event(
                    event,
                    min_push_severity=settings.subscription_events.min_push_severity,
                ):
                    continue

                in_cooldown = await subscription_event_state_repository.is_in_cooldown(
                    chat_id=chat_id,
                    symbol=symbol,
                    event_key=event.event_key,
                    cooldown_minutes=settings.subscription_events.cooldown_minutes,
                    now=now,
                )
                if in_cooldown:
                    continue

                reasons_text = "、".join(event.reasons or [])
                event_lines.append(
                    f"[{event.severity.upper()} {event.score}分] {event.title}："
                    f"{event.summary} 理由：{reasons_text}"
                )
                await subscription_event_state_repository.upsert_state(
                    SubscriptionEventStateRecord(
                        chat_id=chat_id,
                        symbol=symbol,
                        event_key=event.event_key,
                        last_event_value=event.value,
                        last_triggered_at=now,
                    )
                )

            if not event_lines:
                continue

            await application.bot.send_message(
                chat_id=chat_id,
                text=format_subscription_event_message(
                    symbol=symbol,
                    event_lines=event_lines,
                    timestamp=now.astimezone(),
                ),
            )


async def send_no_event_summary(application: Application) -> None:
    settings = application.bot_data["settings"]
    if not settings.subscription_events.enabled or not settings.subscription_events.no_event_summary_enabled:
        return

    user_subscription_repository = application.bot_data["user_subscription_repository"]
    subscription_event_state_repository = application.bot_data["subscription_event_state_repository"]
    subscriptions = await _load_subscription_map(user_subscription_repository)
    if not subscriptions:
        return

    now = datetime.now(tz=UTC)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    for chat_id, symbols in subscriptions.items():
        if not symbols:
            continue

        has_event = await subscription_event_state_repository.has_event_since(
            chat_id=chat_id,
            symbols=symbols,
            since=start_of_day,
        )
        if has_event:
            continue

        await application.bot.send_message(
            chat_id=chat_id,
            text=(
                f"📭 今日事件摘要 {now.astimezone().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "你目前訂閱的幣種截至目前沒有觸發特殊事件。"
            ),
        )


async def _load_subscription_map(user_subscription_repository) -> dict[str, list[str]]:
    subscriptions = await user_subscription_repository.list_all_subscriptions()
    grouped: dict[str, list[str]] = {}
    for subscription in subscriptions:
        grouped.setdefault(subscription.chat_id, []).append(subscription.symbol)
    return grouped


def _filter_supported_symbols(*, coingecko_client, symbols: list[str], context_label: str) -> list[str]:
    supported_symbols: list[str] = []
    for symbol in symbols:
        if coingecko_client.is_supported_symbol(symbol):
            supported_symbols.append(symbol)
            continue
        logger.warning("Skipping unsupported symbol {} during {}", symbol, context_label)
    return supported_symbols


def _resolve_summary_symbols(
    *,
    default_symbols: list[str],
    subscribed_symbols: list[str],
    coingecko_client,
    context_label: str,
) -> list[str]:
    merged_symbols: list[str] = []
    seen: set[str] = set()
    for symbol in [*default_symbols, *subscribed_symbols]:
        normalized = symbol.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        merged_symbols.append(normalized)
    return _filter_supported_symbols(
        coingecko_client=coingecko_client,
        symbols=merged_symbols,
        context_label=context_label,
    )


def _calculate_short_term_change_pct(close_prices: list[float], *, lookback_candles: int) -> float | None:
    if len(close_prices) <= lookback_candles:
        return None

    previous = close_prices[-(lookback_candles + 1)]
    latest = close_prices[-1]
    if previous == 0:
        return None
    return ((latest - previous) / previous) * 100


async def push_strategy_radar(application: Application, *, deliver: bool = True) -> str:
    settings = application.bot_data["settings"]
    if not settings.radar.enabled:
        raise ValueError("雷達功能已停用。")

    coingecko_client = application.bot_data["coingecko_client"]
    binance_futures_client = application.bot_data["binance_futures_client"]
    candle_repository = application.bot_data["candle_repository"]

    static_quotes = await coingecko_client.get_prices(settings.radar.symbols)
    try:
        trending_symbols = set(await coingecko_client.get_trending_symbols())
    except Exception as exc:  # noqa: BLE001
        log_external_data_error("Failed to fetch CoinGecko trending symbols for radar", exc)
        trending_symbols = set()

    quotes = static_quotes
    if settings.radar.dynamic_candidates_enabled:
        try:
            market_quotes = await coingecko_client.get_market_quotes(
                order="volume_desc",
                per_page=max(settings.radar.dynamic_candidate_limit * 2, 50),
            )
        except Exception as exc:  # noqa: BLE001
            log_external_data_error("Failed to fetch CoinGecko markets for radar candidates", exc)
            market_quotes = []
        quotes = build_dynamic_candidate_quotes(
            static_quotes=static_quotes,
            market_quotes=market_quotes,
            trending_symbols=trending_symbols,
            limit=settings.radar.dynamic_candidate_limit,
            min_volume_usd=settings.radar.min_volume_usd,
            min_market_cap_usd=settings.radar.min_market_cap_usd,
            max_market_cap_usd=settings.radar.max_market_cap_usd,
        )

    static_symbols = {str(item["symbol"]).upper() for item in static_quotes}
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
            try:
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
            except Exception:  # noqa: BLE001
                logger.warning("Radar OHLC data unavailable for {}", symbol)

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
                source="static" if symbol.upper() in static_symbols else "dynamic",
            )
        )

    mainstream_entries = build_mainstream_rank(entries, 5)
    mover_entries = build_mover_rank(entries, 8)
    liquid_mid_cap_entries = build_liquid_mid_cap_rank(
        entries,
        limit=8,
        min_volume_usd=settings.radar.min_volume_usd,
        min_market_cap_usd=settings.radar.min_market_cap_usd,
        max_market_cap_usd=settings.radar.max_market_cap_usd,
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
        mainstream_entries=mainstream_entries,
        mover_entries=mover_entries,
        liquid_mid_cap_entries=liquid_mid_cap_entries,
        heat_entries=heat_entries,
        long_entries=long_entries,
        composite_entries=composite_entries,
        ambush_entries=ambush_entries,
        highlights=highlights,
    )

    if deliver and settings.push.chat_id and settings.radar.schedule_enabled:
        await application.bot.send_message(chat_id=settings.push.chat_id, text=message)

    return message
