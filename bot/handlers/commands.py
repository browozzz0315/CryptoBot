from __future__ import annotations

from datetime import UTC, datetime

from telegram import Update
from telegram.ext import ContextTypes

from analysis.screener import top_gainers, top_losers, top_volume
from analysis.signals import build_indicator_snapshot
from bot.formatters import (
    format_alert_created_message,
    format_alert_list_message,
    format_events_status_message,
    format_fear_greed_message,
    format_price_message,
    format_screener_message,
    format_status_message,
    format_subscription_message,
)
from charts.candlestick import render_price_chart
from loguru import logger
from scheduler.jobs import push_strategy_radar
from storage.candles import CandleRecord
from storage.alerts import PriceAlertRecord
from storage.users import UserSubscriptionRecord


async def _reply_text(update: Update, text: str) -> bool:
    message = update.effective_message
    if message is None:
        logger.warning("Cannot reply to update without effective_message: {}", update)
        return False

    await message.reply_text(text)
    return True


async def _reply_photo(update: Update, *, photo, caption: str) -> bool:
    message = update.effective_message
    if message is None:
        logger.warning("Cannot reply with photo to update without effective_message: {}", update)
        return False

    await message.reply_photo(photo=photo, caption=caption)
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply_text(update, 
        "CryptoBot 已啟動。\n"
        "可用指令：\n"
        "/help - 查看指令說明\n"
        "/price BTC - 查詢幣價\n"
        "/fear - 查詢市場情緒\n"
        "/setalert BTC above 70000 - 建立價格警報\n"
        "/listalerts - 查看警報\n"
        "/deletealert 1 - 刪除警報\n"
        "/topgainers - 看漲幅排行\n"
        "/toplosers - 看跌幅排行\n"
        "/topvolume - 看成交量排行\n"
        "/subscribe BTC - 訂閱幣種與事件通知\n"
        "/unsubscribe BTC - 取消訂閱\n"
        "/subscriptions - 查看訂閱\n"
        "/chart BTC - 取得圖表\n"
        "/radar - 取得策略雷達推播\n"
        "/status - 查看 bot 與資料源狀態\n"
        "/events - 查看訂閱事件狀態"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply_text(update, 
        "/start - 初始化機器人\n"
        "/help - 顯示說明\n"
        "/price <symbol> - 查詢指定幣種即時價格\n"
        "/fear - 查詢 Fear & Greed 市場情緒\n"
        "/setalert <symbol> <above|below> <price> - 建立警報\n"
        "/listalerts - 查看啟用中的警報\n"
        "/deletealert <id> - 刪除指定警報\n"
        "/topgainers - 查看漲幅排行\n"
        "/toplosers - 查看跌幅排行\n"
        "/topvolume - 查看成交量排行\n"
        "/subscribe <symbol> - 訂閱幣種與事件通知\n"
        "/unsubscribe <symbol> - 取消訂閱幣種\n"
        "/subscriptions - 查看已訂閱幣種\n"
        "/chart <symbol> - 產生價格圖表\n"
        "/radar - 產生策略雷達摘要\n"
        "/status - 查看 bot、排程與資料源狀態\n"
        "/diag - /status 的別名\n"
        "/events [symbol] - 查看訂閱事件門檻、最近觸發與 cooldown"
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
        await _reply_text(update, str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch price for {}", raw_symbol)
        await _reply_text(update, f"查詢 {raw_symbol.upper()} 價格失敗：{exc}")
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

    await _reply_text(update, message)


async def fear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fear_greed_client = context.application.bot_data["fear_greed_client"]

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch Fear & Greed index")
        await _reply_text(update, f"查詢 Fear & Greed 失敗：{exc}")
        return

    await _reply_text(update, 
        format_fear_greed_message(
            value=sentiment["value"],
            classification=sentiment["classification"],
            updated_at=sentiment["updated_at"],
        )
    )


async def set_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 3:
        await _reply_text(update, "用法：/setalert <symbol> <above|below> <price>")
        return

    raw_symbol, direction, raw_price = context.args
    direction = direction.lower()
    if direction not in {"above", "below"}:
        await _reply_text(update, "方向只接受 above 或 below。")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    alert_repository = context.application.bot_data["alert_repository"]

    try:
        symbol = coingecko_client.validate_symbol(raw_symbol)
        target_price = float(raw_price)
    except ValueError as exc:
        await _reply_text(update, f"警報建立失敗：{exc}")
        return

    if target_price <= 0:
        await _reply_text(update, "價格門檻必須大於 0。")
        return

    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "找不到 chat 資訊，無法建立警報。")
        return

    alert = await alert_repository.create_alert(
        PriceAlertRecord(
            chat_id=str(chat.id),
            symbol=symbol,
            direction=direction,
            target_price=target_price,
        )
    )

    await _reply_text(update, 
        format_alert_created_message(alert.id, alert.symbol, alert.direction, alert.target_price)
    )


async def list_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alert_repository = context.application.bot_data["alert_repository"]
    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "找不到 chat 資訊。")
        return

    alerts = await alert_repository.list_alerts(chat_id=str(chat.id))
    await _reply_text(update, 
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
        await _reply_text(update, "用法：/deletealert <id>")
        return

    try:
        alert_id = int(context.args[0])
    except ValueError:
        await _reply_text(update, "警報 ID 必須是整數。")
        return

    alert_repository = context.application.bot_data["alert_repository"]
    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "找不到 chat 資訊。")
        return

    deleted = await alert_repository.delete_alert(chat_id=str(chat.id), alert_id=alert_id)
    if not deleted:
        await _reply_text(update, f"找不到啟用中的警報 #{alert_id}。")
        return

    await _reply_text(update, f"🗑️ 已刪除警報 #{alert_id}")


async def top_gainers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screener_result(update, context, mode="gainers")


async def top_losers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screener_result(update, context, mode="losers")


async def top_volume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_screener_result(update, context, mode="volume")


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await _reply_text(update, "用法：/subscribe <symbol>")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "找不到 chat 資訊。")
        return

    try:
        symbol = coingecko_client.validate_symbol(context.args[0])
    except ValueError as exc:
        await _reply_text(update, str(exc))
        return

    await user_subscription_repository.upsert_subscription(
        UserSubscriptionRecord(
            chat_id=str(chat.id),
            symbol=symbol,
        )
    )
    await _reply_text(update, 
        f"✅ 已訂閱 {symbol}\n"
        "之後你會收到：\n"
        "1. 固定摘要中的訂閱幣種內容\n"
        "2. 該幣種的事件型通知，例如急漲急跌、RSI 過熱過冷、MACD 交叉、OI 暗流、Funding 偏負"
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await _reply_text(update, "用法：/unsubscribe <symbol>")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "找不到 chat 資訊。")
        return

    try:
        symbol = coingecko_client.normalize_symbol(context.args[0])
    except ValueError as exc:
        await _reply_text(update, str(exc))
        return

    deleted = await user_subscription_repository.delete_subscription(
        chat_id=str(chat.id),
        symbol=symbol,
    )
    if not deleted:
        await _reply_text(update, f"目前沒有訂閱 {symbol}")
        return

    await _reply_text(update, f"🗑️ 已取消訂閱 {symbol}")


async def subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "找不到 chat 資訊。")
        return

    subscriptions = await user_subscription_repository.list_subscriptions(chat_id=str(chat.id))
    await _reply_text(update, 
        format_subscription_message([subscription.symbol for subscription in subscriptions])
    )


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    coingecko_client = context.application.bot_data["coingecko_client"]
    candle_repository = context.application.bot_data["candle_repository"]

    raw_symbol = context.args[0] if context.args else settings.market.default_price_symbol
    try:
        symbol = coingecko_client.validate_symbol(raw_symbol)
    except ValueError as exc:
        await _reply_text(update, str(exc))
        return

    candles = await candle_repository.list_candles(
        symbol=symbol,
        timeframe="4h",
        source="coingecko",
        limit=settings.charts.default_limit,
    )
    if not candles and settings.history.enabled:
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
        candles = await candle_repository.list_candles(
            symbol=symbol,
            timeframe="4h",
            source="coingecko",
            limit=settings.charts.default_limit,
        )

    if not candles:
        await _reply_text(update, "目前沒有可用的圖表資料。")
        return

    chart_path = render_price_chart(symbol=symbol, candles=candles, output_dir=settings.charts.output_dir)
    with chart_path.open("rb") as photo:
        await _reply_photo(update, photo=photo, caption=f"{symbol} 價格圖表")


async def _send_screener_result(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    settings = context.application.bot_data["settings"]
    if not settings.screener.enabled:
        await _reply_text(update, "Screener 功能目前已停用。")
        return

    coingecko_client = context.application.bot_data["coingecko_client"]
    quotes = await coingecko_client.get_prices(settings.screener.symbols)

    if mode == "gainers":
        title = "🚀 24h 漲幅排行"
        ranked = top_gainers(quotes, settings.screener.top_n)
    elif mode == "losers":
        title = "📉 24h 跌幅排行"
        ranked = top_losers(quotes, settings.screener.top_n)
    else:
        title = "💧 24h 成交量排行"
        ranked = top_volume(quotes, settings.screener.top_n)

    await _reply_text(update, format_screener_message(title, ranked))


async def radar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = await push_strategy_radar(context.application, deliver=False)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to generate strategy radar")
        await _reply_text(update, f"產生策略雷達失敗：{exc}")
        return

    await _reply_text(update, message)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    scheduler = context.application.bot_data.get("scheduler")
    coingecko_client = context.application.bot_data["coingecko_client"]
    fear_greed_client = context.application.bot_data["fear_greed_client"]
    binance_futures_client = context.application.bot_data["binance_futures_client"]

    data_sources = []
    try:
        quote = await coingecko_client.get_price(settings.market.default_price_symbol)
    except Exception as exc:  # noqa: BLE001
        logger.warning("CoinGecko status check failed: {}", exc)
        data_sources.append(
            {"name": "CoinGecko", "ok": False, "detail": _short_error_message(exc)}
        )
    else:
        data_sources.append(
            {
                "name": "CoinGecko",
                "ok": True,
                "detail": f"{quote['symbol']} ${float(quote['price']):,.4f}",
            }
        )

    try:
        sentiment = await fear_greed_client.get_latest()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fear & Greed status check failed: {}", exc)
        data_sources.append(
            {"name": "Fear & Greed", "ok": False, "detail": _short_error_message(exc)}
        )
    else:
        data_sources.append(
            {
                "name": "Fear & Greed",
                "ok": True,
                "detail": f"{sentiment['value']} / {sentiment['classification']}",
            }
        )

    try:
        funding = await binance_futures_client.get_latest_funding_rate("BTC")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Binance Futures status check failed: {}", exc)
        data_sources.append(
            {"name": "Binance Futures", "ok": False, "detail": _short_error_message(exc)}
        )
    else:
        data_sources.append(
            {
                "name": "Binance Futures",
                "ok": True,
                "detail": f"BTC funding {float(funding['funding_rate']) * 100:+.3f}%",
            }
        )

    message = format_status_message(
        scheduler_running=bool(scheduler and scheduler.running),
        jobs=_build_scheduler_job_rows(scheduler),
        coingecko_plan=settings.coingecko_api_plan,
        tracked_symbols=settings.market.tracked_symbols,
        subscription_events_enabled=settings.subscription_events.enabled,
        radar_dynamic_enabled=settings.radar.dynamic_candidates_enabled,
        radar_candidate_limit=settings.radar.dynamic_candidate_limit,
        event_min_push_severity=settings.subscription_events.min_push_severity,
        data_sources=data_sources,
    )
    await _reply_text(update, message)


async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    coingecko_client = context.application.bot_data["coingecko_client"]
    user_subscription_repository = context.application.bot_data["user_subscription_repository"]
    subscription_event_state_repository = context.application.bot_data[
        "subscription_event_state_repository"
    ]
    chat = update.effective_chat
    if chat is None:
        await _reply_text(update, "無法取得 chat 資料。")
        return

    filtered_symbol = None
    if context.args:
        try:
            filtered_symbol = coingecko_client.validate_symbol(context.args[0])
        except ValueError as exc:
            await _reply_text(update, str(exc))
            return

    subscriptions = await user_subscription_repository.list_subscriptions(chat_id=str(chat.id))
    subscribed_symbols = [subscription.symbol for subscription in subscriptions]
    query_symbols = [filtered_symbol] if filtered_symbol else subscribed_symbols
    recent_states = await subscription_event_state_repository.list_recent_states(
        chat_id=str(chat.id),
        symbols=query_symbols,
        limit=10,
    )

    message = format_events_status_message(
        symbols=subscribed_symbols,
        filtered_symbol=filtered_symbol,
        thresholds={
            "price_change_threshold_pct": settings.subscription_events.price_change_threshold_pct,
            "short_term_breakout_threshold_pct": settings.subscription_events.short_term_breakout_threshold_pct,
            "short_term_lookback_candles": settings.subscription_events.short_term_lookback_candles,
            "oi_surge_threshold_pct": settings.subscription_events.oi_surge_threshold_pct,
            "funding_negative_threshold_pct": settings.subscription_events.funding_negative_threshold_pct,
            "min_push_severity": settings.subscription_events.min_push_severity,
            "min_confirmations": settings.subscription_events.min_confirmations,
        },
        recent_events=[
            {
                "symbol": state.symbol,
                "event_key": state.event_key,
                "last_event_value": state.last_event_value,
                "last_triggered_at": state.last_triggered_at,
            }
            for state in recent_states
        ],
        cooldown_minutes=settings.subscription_events.cooldown_minutes,
        now=datetime.now(tz=UTC),
    )
    await _reply_text(update, message)


def _build_scheduler_job_rows(scheduler) -> list[dict[str, str]]:
    if scheduler is None:
        return []

    rows: list[dict[str, str]] = []
    for job in scheduler.get_jobs():
        next_run_time = job.next_run_time
        next_run_text = (
            next_run_time.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            if next_run_time
            else "未排定"
        )
        rows.append({"id": job.id, "next_run_time": next_run_text})
    return rows


def _short_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message[:160]
