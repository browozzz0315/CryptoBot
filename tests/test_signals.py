from analysis.signals import build_indicator_snapshot


def test_build_indicator_snapshot_contains_expected_keys() -> None:
    snapshot = build_indicator_snapshot([float(value) for value in range(1, 80)])
    assert set(snapshot.keys()) == {"rsi", "macd", "signal", "histogram", "trend"}
    assert snapshot["trend"] in {"Bullish", "Bearish", "N/A"}
