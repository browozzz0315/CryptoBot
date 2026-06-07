from __future__ import annotations

from datetime import datetime


def format_price_message(symbol: str, price: float, change_24h: float | None) -> str:
    direction = "🟢" if (change_24h or 0) >= 0 else "🔴"
    change_text = "N/A" if change_24h is None else f"{change_24h:+.2f}%"
    return (
        f"📈 {symbol.upper()} 即時價格\n"
        f"價格：`${price:,.4f}`\n"
        f"24h 漲跌：{direction} {change_text}"
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
