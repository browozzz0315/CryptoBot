from bot.formatters import (
    format_fear_greed_message,
    format_market_summary,
    format_price_message,
    format_startup_message,
)
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


def test_format_fear_greed_message_contains_value() -> None:
    result = format_fear_greed_message(
        value=62,
        classification="Greed",
        updated_at=datetime(2026, 6, 7, 12, 0, 0),
    )
    assert "62" in result
    assert "Greed" in result


def test_format_startup_message_contains_symbols() -> None:
    result = format_startup_message(["BTC", "eth"], 5)
    assert "BTC, ETH" in result
    assert "每 5 分鐘" in result
