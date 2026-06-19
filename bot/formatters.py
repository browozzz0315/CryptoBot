from __future__ import annotations

from datetime import UTC, datetime, timedelta

from analysis.radar import RadarEntry


def format_status_message(
    *,
    scheduler_running: bool,
    jobs: list[dict[str, str]],
    coingecko_plan: str,
    tracked_symbols: list[str],
    subscription_events_enabled: bool,
    data_sources: list[dict[str, str | bool]],
) -> str:
    lines = [
        "🧭 CryptoBot 狀態",
        "",
        f"Scheduler：{'運行中' if scheduler_running else '未啟動'}",
        f"CoinGecko plan：{coingecko_plan}",
        f"追蹤幣種：{', '.join(symbol.upper() for symbol in tracked_symbols) or '未設定'}",
        f"事件訂閱：{'啟用' if subscription_events_enabled else '停用'}",
        "",
        "資料源檢查：",
    ]

    for source in data_sources:
        status = "OK" if bool(source["ok"]) else "FAIL"
        lines.append(f"- {source['name']}：{status}，{source['detail']}")

    lines.extend(["", "排程："])
    if not jobs:
        lines.append("- 無已註冊排程")
    else:
        for job in jobs:
            lines.append(f"- {job['id']}：下一次 {job['next_run_time']}")

    return "\n".join(lines)


def format_events_status_message(
    *,
    symbols: list[str],
    filtered_symbol: str | None,
    thresholds: dict[str, float | int],
    recent_events: list[dict[str, str | float | datetime | None]],
    cooldown_minutes: int,
    now: datetime,
) -> str:
    lines = ["📌 訂閱事件狀態", ""]
    if filtered_symbol:
        lines.append(f"查詢幣種：{filtered_symbol.upper()}")
    lines.append(f"訂閱幣種：{', '.join(symbol.upper() for symbol in symbols) or '尚未訂閱'}")
    lines.extend(
        [
            "",
            "目前門檻：",
            f"- 24h 急漲急跌：±{float(thresholds['price_change_threshold_pct']):.2f}%",
            f"- 短線突破 / 跌破：±{float(thresholds['short_term_breakout_threshold_pct']):.2f}%",
            f"- 短線回看 K 線：{int(thresholds['short_term_lookback_candles'])} 根",
            f"- OI 暗流：+{float(thresholds['oi_surge_threshold_pct']):.2f}%",
            f"- Funding 偏負：{float(thresholds['funding_negative_threshold_pct']):+.3f}%",
            f"- Cooldown：{cooldown_minutes} 分鐘",
            "",
            "最近事件：",
        ]
    )

    if not recent_events:
        lines.append("- 尚無事件紀錄")
        return "\n".join(lines)

    reference_time = _ensure_aware_datetime(now)
    for event in recent_events:
        last_triggered_at = event.get("last_triggered_at")
        triggered_text = "N/A"
        cooldown_text = "不在 cooldown"
        if isinstance(last_triggered_at, datetime):
            triggered_at = _ensure_aware_datetime(last_triggered_at)
            triggered_text = triggered_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            cooldown_until = triggered_at + timedelta(minutes=cooldown_minutes)
            if reference_time < cooldown_until:
                cooldown_text = f"cooldown 到 {cooldown_until.astimezone().strftime('%H:%M:%S')}"

        value = event.get("last_event_value")
        value_text = "N/A" if value is None else f"{float(value):+.3f}"
        lines.append(
            f"- {str(event['symbol']).upper()} {event['event_key']}：{value_text}，"
            f"{triggered_text}，{cooldown_text}"
        )

    return "\n".join(lines)


def format_startup_message(tracked_symbols: list[str], interval_minutes: int) -> str:
    symbols_text = ", ".join(symbol.upper() for symbol in tracked_symbols)
    return (
        "🤖 CryptoBot 已啟動\n"
        "Telegram 連線已建立，排程系統已啟用。\n"
        f"追蹤幣種：{symbols_text}\n"
        f"推播頻率：每 {interval_minutes} 分鐘\n"
        "價格與市場情緒資料會在查詢或排程執行時抓取。"
    )


def format_price_message(
    *,
    symbol: str,
    name: str,
    price: float,
    change_24h: float | None,
    quote_currency: str,
    market_cap: float,
    total_volume: float,
    high_24h: float,
    low_24h: float,
    updated_at: datetime,
    indicators: dict[str, float | None | str] | None = None,
) -> str:
    direction = "🟢" if (change_24h or 0) >= 0 else "🔴"
    change_text = "N/A" if change_24h is None else f"{change_24h:+.2f}%"
    currency = quote_currency.upper()
    message = (
        f"📈 {name} ({symbol.upper()})\n"
        f"價格：{price:,.4f} {currency}\n"
        f"24h 漲跌：{direction} {change_text}\n"
        f"24h 區間：{low_24h:,.4f} - {high_24h:,.4f} {currency}\n"
        f"24h 成交量：{total_volume:,.0f} {currency}\n"
        f"市值：{market_cap:,.0f} {currency}\n"
        f"資料時間：{updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    if indicators:
        rsi_value = indicators.get("rsi")
        macd_value = indicators.get("macd")
        signal_value = indicators.get("signal")
        trend = indicators.get("trend")
        message += (
            "\n\n"
            "📐 技術指標\n"
            f"RSI(14)：{_format_optional_number(rsi_value)}\n"
            f"MACD：{_format_optional_number(macd_value)}\n"
            f"Signal：{_format_optional_number(signal_value)}\n"
            f"趨勢：{trend}"
        )
    return message


def format_fear_greed_message(value: int, classification: str, updated_at: datetime) -> str:
    return (
        "😱 市場情緒指數\n"
        f"Fear & Greed：{value}（{classification}）\n"
        f"更新時間：{updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def format_market_summary(summary_rows: list[dict[str, float | str]], timestamp: datetime) -> str:
    header = f"📊 市場快報 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    lines = [header, ""]

    for row in summary_rows:
        symbol = str(row["symbol"]).upper()
        price = float(row["price"])
        change_24h = float(row["change_24h"])
        direction = "🟢" if change_24h >= 0 else "🔴"
        lines.append(f"{symbol:<5} ${price:,.4f}  {direction} {change_24h:+.2f}%")

    return "\n".join(lines)


def format_alert_created_message(alert_id: int, symbol: str, direction: str, target_price: float) -> str:
    direction_text = "突破" if direction == "above" else "跌破"
    return f"🔔 已建立警報 #{alert_id}\n條件：{symbol.upper()} {direction_text} {target_price:,.4f}"


def format_alert_list_message(alerts: list[dict[str, int | float | str]]) -> str:
    if not alerts:
        return "目前沒有啟用中的價格警報。"

    lines = ["📋 價格警報列表", ""]
    for alert in alerts:
        direction_text = "above" if alert["direction"] == "above" else "below"
        lines.append(
            f"#{alert['id']}  {alert['symbol']}  {direction_text}  {float(alert['target_price']):,.4f}"
        )
    return "\n".join(lines)


def format_alert_triggered_message(symbol: str, direction: str, target_price: float, current_price: float) -> str:
    direction_text = "突破" if direction == "above" else "跌破"
    return (
        f"🚨 價格警報觸發\n"
        f"{symbol.upper()} 已{direction_text} {target_price:,.4f}\n"
        f"目前價格：{current_price:,.4f}"
    )


def format_screener_message(title: str, quotes: list[dict[str, float | str]]) -> str:
    lines = [title, ""]
    for quote in quotes:
        lines.append(
            f"{str(quote['symbol']).upper():<6} "
            f"{float(quote['price']):,.4f}  "
            f"{float(quote['change_24h']):+,.2f}%  "
            f"Vol {float(quote['total_volume']):,.0f}"
        )
    return "\n".join(lines)


def format_subscription_message(symbols: list[str]) -> str:
    if not symbols:
        return "目前沒有任何訂閱幣種。"
    return "🔖 已訂閱幣種\n" + "\n".join(f"- {symbol.upper()}" for symbol in symbols)


def format_subscription_event_message(
    *,
    symbol: str,
    event_lines: list[str],
    timestamp: datetime,
) -> str:
    header = f"🚨 訂閱事件通知 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    lines = [header, f"標的：{symbol.upper()}", ""]
    lines.extend(f"- {line}" for line in event_lines)
    return "\n".join(lines)


def format_radar_message(
    *,
    timestamp: datetime,
    heat_entries: list[RadarEntry],
    long_entries: list[RadarEntry],
    composite_entries: list[tuple[RadarEntry, int]],
    ambush_entries: list[tuple[RadarEntry, int]],
    highlights: list[str],
) -> str:
    lines = [f"🏦 策略雷達推播", f"⏰ {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}", ""]
    lines.append("🔥 熱度榜")
    lines.extend(_format_heat_entries(heat_entries))
    lines.append("")
    lines.append("🔥 追多")
    lines.extend(_format_long_entries(long_entries))
    lines.append("")
    lines.append("📊 綜合")
    lines.extend(_format_scored_entries(composite_entries))
    lines.append("")
    lines.append("🎯 埋伏")
    lines.extend(_format_scored_entries(ambush_entries))
    lines.append("")
    lines.append("💡 值得關注")
    if highlights:
        lines.extend(f"  {line}" for line in highlights)
    else:
        lines.append("  目前沒有明確的額外關注摘要。")
    return "\n".join(lines)


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _format_optional_number(value: float | None | str) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return f"{value:.4f}"


def _format_heat_entries(entries: list[RadarEntry]) -> list[str]:
    if not entries:
        return ["  無資料"]
    lines: list[str] = []
    for entry in entries:
        tags = []
        if entry.trending:
            tags.append("🌐CG熱搜")
        if entry.oi_change_pct is not None:
            tags.append(f"⚡OI{entry.oi_change_pct:+.0f}%")
        if entry.sideways_days > 0:
            tags.append(f"💤{entry.sideways_days}天")
        lines.append(
            f"  {entry.symbol:<8} ~${entry.market_cap/1_000_000:,.0f}M 漲{entry.change_24h:+.0f}% | {' '.join(tags)}"
        )
    return lines


def _format_long_entries(entries: list[RadarEntry]) -> list[str]:
    if not entries:
        return ["  無資料"]
    return [
        f"  {entry.symbol:<8} 費率{'N/A' if entry.funding_rate is None else f'{entry.funding_rate:+.3f}%'} | 漲{entry.change_24h:+.0f}% | ~${entry.market_cap/1_000_000:,.0f}M"
        for entry in entries
    ]


def _format_scored_entries(entries: list[tuple[RadarEntry, int]]) -> list[str]:
    if not entries:
        return ["  無資料"]
    lines: list[str] = []
    for entry, score in entries:
        oi_text = "N/A" if entry.oi_change_pct is None else f"{entry.oi_change_pct:+.0f}%"
        funding_text = "N/A" if entry.funding_rate is None else f"{entry.funding_rate:+.3f}%"
        lines.append(
            f"  {entry.symbol:<8} {score}分 | 🧊{funding_text} 💎${entry.market_cap/1_000_000:,.0f}M 💤{entry.sideways_days}天 ⚡OI{oi_text}"
        )
    return lines
