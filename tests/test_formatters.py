from bot.formatters import format_market_summary, format_price_message
from datetime import datetime


def test_format_price_message_contains_symbol() -> None:
    result = format_price_message("BTC", 100000.0, 3.5)
    assert "BTC" in result
    assert "3.50%" in result


def test_format_market_summary_contains_rows() -> None:
    result = format_market_summary(
        [{"symbol": "BTC", "price": 100000.0, "change_24h": 2.1}],
        datetime(2026, 6, 7, 12, 0, 0),
    )
    assert "BTC" in result
    assert "2.10%" in result
