import asyncio
import sys
from types import SimpleNamespace

import httpx
from loguru import logger
from telegram.error import NetworkError

from bot.main import telegram_error_handler
from utils.logger import (
    external_error_summary,
    is_transient_external_error,
    setup_logger,
)


def test_setup_logger_writes_warning_file_with_timestamp(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    setup_logger("INFO")
    logger.warning("sample warning")
    logger.complete()

    log_file = tmp_path / "runtime" / "logs" / "warnings-errors.log"
    content = log_file.read_text(encoding="utf-8")

    assert "WARNING" in content
    assert "sample warning" in content
    assert content[:4].isdigit()
    assert content[4] == "-"

    logger.remove()
    logger.add(sys.stderr, level="INFO")


def test_http_5xx_is_transient_external_error() -> None:
    request = httpx.Request("GET", "https://api.example.test/data")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("server error", request=request, response=response)

    assert is_transient_external_error(error) is True
    assert "status_code=500" in external_error_summary(error)
    assert "https://api.example.test/data" in external_error_summary(error)


def test_value_error_is_not_transient_external_error() -> None:
    assert is_transient_external_error(ValueError("bad payload")) is False


def test_telegram_network_error_handler_logs_warning() -> None:
    messages: list[str] = []
    sink_id = logger.add(messages.append, level="WARNING", format="{level}|{message}")

    async def run_case() -> None:
        context = SimpleNamespace(error=NetworkError("Bad Gateway"))
        await telegram_error_handler(update=None, context=context)

    try:
        asyncio.run(run_case())
    finally:
        logger.remove(sink_id)

    assert any("WARNING|Telegram transient network error" in message for message in messages)
    assert any("Bad Gateway" in message for message in messages)
