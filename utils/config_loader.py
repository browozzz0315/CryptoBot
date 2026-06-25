from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    timezone: str
    log_level: str


@dataclass(slots=True)
class MarketConfig:
    quote_currency: str
    tracked_symbols: list[str]
    default_price_symbol: str


@dataclass(slots=True)
class PushConfig:
    enabled: bool
    interval_minutes: int
    chat_id: str | None
    schedule_mode: str
    cron_hours: list[int]
    cron_minute: int


@dataclass(slots=True)
class StorageConfig:
    database_url: str


@dataclass(slots=True)
class HistoryConfig:
    enabled: bool
    sync_on_startup: bool
    sync_interval_minutes: int
    ohlc_days: int


@dataclass(slots=True)
class AlertsConfig:
    enabled: bool
    check_interval_minutes: int


@dataclass(slots=True)
class ScreenerConfig:
    enabled: bool
    symbols: list[str]
    top_n: int


@dataclass(slots=True)
class ChartsConfig:
    enabled: bool
    output_dir: str
    default_limit: int


@dataclass(slots=True)
class RadarConfig:
    enabled: bool
    schedule_enabled: bool
    interval_minutes: int
    schedule_mode: str
    cron_hours: list[int]
    cron_minute: int
    symbols: list[str]
    heat_top_n: int
    long_top_n: int
    composite_top_n: int
    ambush_top_n: int
    sideways_lookback_candles: int
    sideways_threshold_pct: float
    dynamic_candidates_enabled: bool
    dynamic_candidate_limit: int
    min_volume_usd: float
    min_market_cap_usd: float
    max_market_cap_usd: float


@dataclass(slots=True)
class SubscriptionEventsConfig:
    enabled: bool
    check_interval_minutes: int
    cooldown_minutes: int
    no_event_summary_enabled: bool
    no_event_summary_hours: list[int]
    no_event_summary_minute: int
    history_limit: int
    min_push_severity: str
    min_confirmations: int
    medium_summary_enabled: bool
    price_change_threshold_pct: float
    short_term_breakout_threshold_pct: float
    short_term_lookback_candles: int
    rsi_overbought: float
    rsi_oversold: float
    oi_surge_threshold_pct: float
    price_flat_threshold_pct: float
    funding_negative_threshold_pct: float


@dataclass(slots=True)
class CoinGeckoConfig:
    base_url: str
    api_plan: str


@dataclass(slots=True)
class FearGreedConfig:
    base_url: str


@dataclass(slots=True)
class BinanceFuturesConfig:
    base_url: str


@dataclass(slots=True)
class ApiConfig:
    coingecko: CoinGeckoConfig
    fear_greed: FearGreedConfig
    binance_futures: BinanceFuturesConfig


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    coingecko_api_key: str | None
    coingecko_api_plan: str
    app: AppConfig
    market: MarketConfig
    push: PushConfig
    storage: StorageConfig
    history: HistoryConfig
    alerts: AlertsConfig
    screener: ScreenerConfig
    charts: ChartsConfig
    radar: RadarConfig
    subscription_events: SubscriptionEventsConfig
    api: ApiConfig


def load_settings(config_path: str = "config.yaml") -> Settings:
    load_dotenv()

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"找不到設定檔：{config_path}")

    with config_file.open("r", encoding="utf-8") as file:
        raw_config: dict[str, Any] = yaml.safe_load(file) or {}

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise ValueError("缺少 TELEGRAM_BOT_TOKEN，請先在 .env 設定。")

    push_chat_id = os.getenv("TELEGRAM_DEFAULT_CHAT_ID") or raw_config["push"].get("chat_id")
    coingecko_api_plan = str(
        os.getenv(
            "COINGECKO_API_PLAN",
            raw_config["api"]["coingecko"].get("plan", "demo"),
        )
    ).lower()
    if coingecko_api_plan not in {"demo", "pro"}:
        raise ValueError("COINGECKO_API_PLAN 僅支援 demo 或 pro。")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        coingecko_api_key=os.getenv("COINGECKO_API_KEY") or None,
        coingecko_api_plan=coingecko_api_plan,
        app=AppConfig(
            timezone=raw_config["app"]["timezone"],
            log_level=os.getenv("LOG_LEVEL", raw_config["app"]["log_level"]),
        ),
        market=MarketConfig(
            quote_currency=raw_config["market"]["quote_currency"],
            tracked_symbols=raw_config["market"]["tracked_symbols"],
            default_price_symbol=raw_config["market"]["default_price_symbol"],
        ),
        push=PushConfig(
            enabled=bool(raw_config["push"]["enabled"]),
            interval_minutes=int(raw_config["push"]["interval_minutes"]),
            chat_id=str(push_chat_id) if push_chat_id else None,
            schedule_mode=str(raw_config["push"].get("schedule_mode", "interval")).lower(),
            cron_hours=[int(hour) for hour in raw_config["push"].get("cron_hours", [])],
            cron_minute=int(raw_config["push"].get("cron_minute", 0)),
        ),
        storage=StorageConfig(
            database_url=os.getenv(
                "DATABASE_URL",
                raw_config["storage"]["database_url"],
            ),
        ),
        history=HistoryConfig(
            enabled=bool(raw_config["history"]["enabled"]),
            sync_on_startup=bool(raw_config["history"]["sync_on_startup"]),
            sync_interval_minutes=int(raw_config["history"]["sync_interval_minutes"]),
            ohlc_days=int(raw_config["history"]["ohlc_days"]),
        ),
        alerts=AlertsConfig(
            enabled=bool(raw_config["alerts"]["enabled"]),
            check_interval_minutes=int(raw_config["alerts"]["check_interval_minutes"]),
        ),
        screener=ScreenerConfig(
            enabled=bool(raw_config["screener"]["enabled"]),
            symbols=raw_config["screener"]["symbols"],
            top_n=int(raw_config["screener"]["top_n"]),
        ),
        charts=ChartsConfig(
            enabled=bool(raw_config["charts"]["enabled"]),
            output_dir=raw_config["charts"]["output_dir"],
            default_limit=int(raw_config["charts"]["default_limit"]),
        ),
        radar=RadarConfig(
            enabled=bool(raw_config["radar"]["enabled"]),
            schedule_enabled=bool(raw_config["radar"]["schedule_enabled"]),
            interval_minutes=int(raw_config["radar"]["interval_minutes"]),
            schedule_mode=str(raw_config["radar"].get("schedule_mode", "interval")).lower(),
            cron_hours=[int(hour) for hour in raw_config["radar"].get("cron_hours", [])],
            cron_minute=int(raw_config["radar"].get("cron_minute", 0)),
            symbols=raw_config["radar"]["symbols"],
            heat_top_n=int(raw_config["radar"]["heat_top_n"]),
            long_top_n=int(raw_config["radar"]["long_top_n"]),
            composite_top_n=int(raw_config["radar"]["composite_top_n"]),
            ambush_top_n=int(raw_config["radar"]["ambush_top_n"]),
            sideways_lookback_candles=int(raw_config["radar"]["sideways_lookback_candles"]),
            sideways_threshold_pct=float(raw_config["radar"]["sideways_threshold_pct"]),
            dynamic_candidates_enabled=bool(raw_config["radar"].get("dynamic_candidates_enabled", False)),
            dynamic_candidate_limit=int(raw_config["radar"].get("dynamic_candidate_limit", len(raw_config["radar"]["symbols"]))),
            min_volume_usd=float(raw_config["radar"].get("min_volume_usd", 0)),
            min_market_cap_usd=float(raw_config["radar"].get("min_market_cap_usd", 0)),
            max_market_cap_usd=float(raw_config["radar"].get("max_market_cap_usd", 0)),
        ),
        subscription_events=SubscriptionEventsConfig(
            enabled=bool(raw_config["subscription_events"]["enabled"]),
            check_interval_minutes=int(raw_config["subscription_events"]["check_interval_minutes"]),
            cooldown_minutes=int(raw_config["subscription_events"]["cooldown_minutes"]),
            no_event_summary_enabled=bool(raw_config["subscription_events"].get("no_event_summary_enabled", False)),
            no_event_summary_hours=[int(hour) for hour in raw_config["subscription_events"].get("no_event_summary_hours", [])],
            no_event_summary_minute=int(raw_config["subscription_events"].get("no_event_summary_minute", 0)),
            history_limit=int(raw_config["subscription_events"]["history_limit"]),
            min_push_severity=str(raw_config["subscription_events"].get("min_push_severity", "high")).lower(),
            min_confirmations=int(raw_config["subscription_events"].get("min_confirmations", 2)),
            medium_summary_enabled=bool(raw_config["subscription_events"].get("medium_summary_enabled", True)),
            price_change_threshold_pct=float(raw_config["subscription_events"]["price_change_threshold_pct"]),
            short_term_breakout_threshold_pct=float(raw_config["subscription_events"].get("short_term_breakout_threshold_pct", 2.5)),
            short_term_lookback_candles=int(raw_config["subscription_events"].get("short_term_lookback_candles", 4)),
            rsi_overbought=float(raw_config["subscription_events"]["rsi_overbought"]),
            rsi_oversold=float(raw_config["subscription_events"]["rsi_oversold"]),
            oi_surge_threshold_pct=float(raw_config["subscription_events"]["oi_surge_threshold_pct"]),
            price_flat_threshold_pct=float(raw_config["subscription_events"]["price_flat_threshold_pct"]),
            funding_negative_threshold_pct=float(raw_config["subscription_events"]["funding_negative_threshold_pct"]),
        ),
        api=ApiConfig(
            coingecko=CoinGeckoConfig(
                base_url=raw_config["api"]["coingecko"]["base_url"],
                api_plan=str(raw_config["api"]["coingecko"].get("plan", "demo")).lower(),
            ),
            fear_greed=FearGreedConfig(
                base_url=raw_config["api"]["fear_greed"]["base_url"],
            ),
            binance_futures=BinanceFuturesConfig(
                base_url=raw_config["api"]["binance_futures"]["base_url"],
            ),
        ),
    )
