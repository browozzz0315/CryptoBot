from __future__ import annotations

from analysis.indicators import macd, rsi


def build_indicator_snapshot(close_prices: list[float]) -> dict[str, float | None | str]:
    if not close_prices:
        return {
            "rsi": None,
            "macd": None,
            "signal": None,
            "histogram": None,
            "trend": "N/A",
        }

    rsi_series = rsi(close_prices, 14)
    macd_series = macd(close_prices)

    latest_rsi = _last_value(rsi_series)
    latest_macd = _last_value(macd_series["macd"])
    latest_signal = _last_value(macd_series["signal"])
    latest_histogram = _last_value(macd_series["histogram"])

    trend = "N/A"
    if latest_macd is not None and latest_signal is not None:
        trend = "Bullish" if latest_macd >= latest_signal else "Bearish"

    return {
        "rsi": latest_rsi,
        "macd": latest_macd,
        "signal": latest_signal,
        "histogram": latest_histogram,
        "trend": trend,
    }


def _last_value(series: list[float | None]) -> float | None:
    for value in reversed(series):
        if value is not None:
            return value
    return None
