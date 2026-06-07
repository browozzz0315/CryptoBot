from analysis.indicators import ema, macd, rsi, sma


def test_sma_returns_expected_average() -> None:
    result = sma([1, 2, 3, 4, 5], 3)
    assert result[-1] == 4


def test_ema_seeds_after_period() -> None:
    result = ema([1, 2, 3, 4, 5, 6], 3)
    assert result[1] is None
    assert result[2] is not None


def test_rsi_returns_series_length() -> None:
    values = [44, 44.15, 43.9, 44.35, 44.6, 45.0, 44.8, 45.2, 45.6, 45.5, 45.8, 46.1, 45.9, 46.2, 46.5]
    result = rsi(values, 14)
    assert len(result) == len(values)
    assert result[-1] is not None


def test_macd_contains_all_series() -> None:
    result = macd([float(value) for value in range(1, 60)])
    assert set(result.keys()) == {"macd", "signal", "histogram"}
