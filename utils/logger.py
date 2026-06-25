from __future__ import annotations

import sys
from pathlib import Path

import httpx
from loguru import logger


def setup_logger(log_level: str) -> None:
    log_dir = Path("runtime/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    )
    logger.add(
        log_dir / "warnings-errors.log",
        level="WARNING",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )


def is_transient_external_error(error: BaseException) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        return status_code in {408, 429} or status_code >= 500
    return isinstance(error, (httpx.TimeoutException, httpx.TransportError))


def external_error_summary(error: BaseException) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        request = error.request
        return (
            f"{type(error).__name__}(status_code={error.response.status_code}, "
            f"url={request.url})"
        )
    return f"{type(error).__name__}: {error}"


def log_external_data_error(message: str, error: BaseException, *args: object) -> None:
    if is_transient_external_error(error):
        logger.warning("{}: {}", message.format(*args), external_error_summary(error))
        return
    logger.opt(exception=error).error(message, *args)
