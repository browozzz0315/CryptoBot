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
) -> str:
    direction = "🟢" if (change_24h or 0) >= 0 else "🔴"
    change_text = "N/A" if change_24h is None else f"{change_24h:+.2f}%"
    currency = quote_currency.upper()
    return (
        f"📈 {name} ({symbol.upper()})\n"
        f"價格：{price:,.4f} {currency}\n"
        f"24h 漲跌：{direction} {change_text}\n"
        f"24h 區間：{low_24h:,.4f} - {high_24h:,.4f} {currency}\n"
        f"24h 成交量：{total_volume:,.0f} {currency}\n"
        f"市值：{market_cap:,.0f} {currency}\n"
        f"資料時間：{updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )


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
