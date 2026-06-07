from __future__ import annotations

import sys
from pathlib import Path

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
        rotation="5 MB",
        retention=10,
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )
