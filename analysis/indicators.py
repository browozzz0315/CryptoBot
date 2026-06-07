from __future__ import annotations


def sma(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period 必須大於 0")

    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            result.append(None)
            continue
        window = values[index + 1 - period : index + 1]
        result.append(sum(window) / period)
    return result


def ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period 必須大於 0")
    if not values:
        return []

    multiplier = 2 / (period + 1)
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    seed = sum(values[:period]) / period
    result[period - 1] = seed
    previous = seed

    for index in range(period, len(values)):
        current = (values[index] - previous) * multiplier + previous
        result[index] = current
        previous = current

    return result


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    if period <= 0:
        raise ValueError("period 必須大於 0")
    if len(values) < period + 1:
        return [None] * len(values)

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    result: list[float | None] = [None] * len(values)
    result[period] = _to_rsi(avg_gain, avg_loss)

    for index in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[index]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[index]) / period
        result[index + 1] = _to_rsi(avg_gain, avg_loss)

    return result


def macd(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> dict[str, list[float | None]]:
    fast = ema(values, fast_period)
    slow = ema(values, slow_period)

    macd_line: list[float | None] = []
    for fast_value, slow_value in zip(fast, slow, strict=False):
        if fast_value is None or slow_value is None:
            macd_line.append(None)
        else:
            macd_line.append(fast_value - slow_value)

    compact_line = [value for value in macd_line if value is not None]
    signal_compact = ema(compact_line, signal_period)
    signal_line: list[float | None] = []
    compact_index = 0
    for value in macd_line:
        if value is None:
            signal_line.append(None)
        else:
            signal_line.append(signal_compact[compact_index])
            compact_index += 1

    histogram: list[float | None] = []
    for macd_value, signal_value in zip(macd_line, signal_line, strict=False):
        if macd_value is None or signal_value is None:
            histogram.append(None)
        else:
            histogram.append(macd_value - signal_value)

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def _to_rsi(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
