from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from utils.config_loader import load_settings


def test_load_settings_parses_subscription_event_short_term_fields() -> None:
    config = {
        "app": {"timezone": "Asia/Taipei", "log_level": "INFO"},
        "market": {
            "quote_currency": "usd",
            "tracked_symbols": ["BTC"],
            "default_price_symbol": "BTC",
        },
        "push": {
            "enabled": True,
            "interval_minutes": 180,
            "schedule_mode": "interval",
            "cron_hours": [],
            "cron_minute": 0,
            "chat_id": None,
        },
        "storage": {"database_url": "sqlite+aiosqlite:///./runtime/test.db"},
        "history": {
            "enabled": True,
            "sync_on_startup": False,
            "sync_interval_minutes": 360,
            "ohlc_days": 30,
        },
        "alerts": {"enabled": True, "check_interval_minutes": 1},
        "screener": {"enabled": True, "symbols": ["BTC"], "top_n": 5},
        "charts": {
            "enabled": True,
            "output_dir": "runtime/charts",
            "default_limit": 60,
        },
        "radar": {
            "enabled": True,
            "schedule_enabled": True,
            "interval_minutes": 180,
            "schedule_mode": "cron",
            "cron_hours": [6, 14, 22],
            "cron_minute": 0,
            "symbols": ["BTC"],
            "heat_top_n": 8,
            "long_top_n": 5,
            "composite_top_n": 8,
            "ambush_top_n": 8,
            "sideways_lookback_candles": 30,
            "sideways_threshold_pct": 12.0,
        },
        "subscription_events": {
            "enabled": True,
            "check_interval_minutes": 3,
            "cooldown_minutes": 180,
            "no_event_summary_enabled": True,
            "no_event_summary_hours": [9, 18],
            "no_event_summary_minute": 5,
            "history_limit": 80,
            "price_change_threshold_pct": 5.0,
            "short_term_breakout_threshold_pct": 2.5,
            "short_term_lookback_candles": 4,
            "rsi_overbought": 70.0,
            "rsi_oversold": 30.0,
            "oi_surge_threshold_pct": 8.0,
            "price_flat_threshold_pct": 2.5,
            "funding_negative_threshold_pct": -0.015,
        },
        "api": {
            "coingecko": {
                "base_url": "https://api.coingecko.com/api/v3",
                "plan": "demo",
            },
            "fear_greed": {"base_url": "https://api.alternative.me"},
            "binance_futures": {"base_url": "https://fapi.binance.com"},
        },
    }

    with TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "config.yaml"
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test-token", "COINGECKO_API_PLAN": "pro"},
            clear=True,
        ):
            settings = load_settings(str(config_path))

    assert settings.coingecko_api_plan == "pro"
    assert settings.subscription_events.short_term_breakout_threshold_pct == 2.5
    assert settings.subscription_events.short_term_lookback_candles == 4
    assert settings.subscription_events.oi_surge_threshold_pct == 8.0
    assert settings.subscription_events.funding_negative_threshold_pct == -0.015
