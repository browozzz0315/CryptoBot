from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("runtime/mplconfig").resolve()))

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from storage.models import Candle


def render_price_chart(*, symbol: str, candles: list[Candle], output_dir: str) -> Path:
    if not candles:
        raise ValueError("沒有可用的 K 線資料可繪圖。")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / f"{symbol.lower()}_chart.png"

    candles = list(reversed(candles))
    timestamps = [candle.close_time for candle in candles]
    closes = [candle.close_price for candle in candles]
    highs = [candle.high_price for candle in candles]
    lows = [candle.low_price for candle in candles]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, closes, label="Close", linewidth=2)
    ax.fill_between(timestamps, lows, highs, alpha=0.15, label="High/Low Range")
    ax.set_title(f"{symbol.upper()} Price Chart")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(file_path, dpi=150)
    plt.close(fig)
    return file_path
