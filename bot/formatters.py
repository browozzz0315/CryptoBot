from __future__ import annotations

from datetime import datetime


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


def _format_optional_number(value: float | None | str) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return f"{value:.4f}"
