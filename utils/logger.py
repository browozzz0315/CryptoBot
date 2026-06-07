from __future__ import annotations

import sys

from loguru import logger


def setup_logger(log_level: str) -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    )
