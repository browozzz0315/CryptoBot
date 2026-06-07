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
class CoinGeckoConfig:
    base_url: str


@dataclass(slots=True)
class FearGreedConfig:
    base_url: str


@dataclass(slots=True)
class ApiConfig:
    coingecko: CoinGeckoConfig
    fear_greed: FearGreedConfig


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    coingecko_api_key: str | None
    app: AppConfig
    market: MarketConfig
    push: PushConfig
    storage: StorageConfig
    history: HistoryConfig
    alerts: AlertsConfig
    screener: ScreenerConfig
    charts: ChartsConfig
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

    return Settings(
        telegram_bot_token=telegram_bot_token,
        coingecko_api_key=os.getenv("COINGECKO_API_KEY") or None,
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
        api=ApiConfig(
            coingecko=CoinGeckoConfig(
                base_url=raw_config["api"]["coingecko"]["base_url"],
            ),
            fear_greed=FearGreedConfig(
                base_url=raw_config["api"]["fear_greed"]["base_url"],
            ),
        ),
    )
