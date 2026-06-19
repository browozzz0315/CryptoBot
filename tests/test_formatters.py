from bot.formatters import (
    format_events_status_message,
    format_fear_greed_message,
    format_market_summary,
    format_price_message,
    format_startup_message,
    format_status_message,
)
from datetime import datetime


def test_format_price_message_contains_symbol() -> None:
    result = format_price_message(
        symbol="BTC",
        name="Bitcoin",
        price=100000.0,
        change_24h=3.5,
        quote_currency="usd",
        market_cap=1_000_000_000.0,
        total_volume=500_000_000.0,
        high_24h=101000.0,
        low_24h=98000.0,
        updated_at=datetime(2026, 6, 7, 12, 0, 0),
    )
    assert "Bitcoin (BTC)" in result
    assert "3.50%" in result
    assert "資料時間" in result


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


def test_format_status_message_contains_jobs_and_data_sources() -> None:
    result = format_status_message(
        scheduler_running=True,
        jobs=[{"id": "subscription_event_check", "next_run_time": "2026-06-19 12:00:00"}],
        coingecko_plan="demo",
        tracked_symbols=["BTC", "ETH"],
        subscription_events_enabled=True,
        data_sources=[
            {"name": "CoinGecko", "ok": True, "detail": "BTC $100,000"},
            {"name": "Binance Futures", "ok": False, "detail": "timeout"},
        ],
    )

    assert "CryptoBot 狀態" in result
    assert "subscription_event_check" in result
    assert "CoinGecko：OK" in result
    assert "Binance Futures：FAIL" in result


def test_format_events_status_message_handles_empty_events() -> None:
    result = format_events_status_message(
        symbols=["BTC"],
        filtered_symbol=None,
        thresholds={
            "price_change_threshold_pct": 5.0,
            "short_term_breakout_threshold_pct": 2.5,
            "short_term_lookback_candles": 4,
            "oi_surge_threshold_pct": 8.0,
            "funding_negative_threshold_pct": -0.015,
        },
        recent_events=[],
        cooldown_minutes=180,
        now=datetime(2026, 6, 19, 12, 0, 0),
    )

    assert "訂閱事件狀態" in result
    assert "BTC" in result
    assert "尚無事件紀錄" in result


def test_format_events_status_message_marks_cooldown() -> None:
    result = format_events_status_message(
        symbols=["BTC"],
        filtered_symbol="BTC",
        thresholds={
            "price_change_threshold_pct": 5.0,
            "short_term_breakout_threshold_pct": 2.5,
            "short_term_lookback_candles": 4,
            "oi_surge_threshold_pct": 8.0,
            "funding_negative_threshold_pct": -0.015,
        },
        recent_events=[
            {
                "symbol": "BTC",
                "event_key": "price_surge_up",
                "last_event_value": 6.5,
                "last_triggered_at": datetime(2026, 6, 19, 11, 0, 0),
            }
        ],
        cooldown_minutes=180,
        now=datetime(2026, 6, 19, 12, 0, 0),
    )

    assert "price_surge_up" in result
    assert "cooldown 到" in result
