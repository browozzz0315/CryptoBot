from analysis.signals import detect_macd_cross, detect_subscription_events


def test_detect_macd_cross_bullish() -> None:
    close_prices = [
        100.0,
        99.0,
        98.0,
        97.0,
        96.0,
        95.0,
        94.0,
        93.0,
        92.0,
        91.0,
        90.0,
        89.0,
        88.0,
        87.0,
        86.0,
        87.0,
        88.0,
        89.0,
        90.0,
        91.0,
        92.0,
        93.0,
        94.0,
        95.0,
        96.0,
        97.0,
        98.0,
        99.0,
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        105.0,
        106.0,
    ]
    assert detect_macd_cross(close_prices) in {"bullish", None}


def test_detect_subscription_events_generates_multiple_events() -> None:
    close_prices = [100.0] * 40
    events = detect_subscription_events(
        symbol="BTC",
        close_prices=close_prices,
        change_24h=9.5,
        short_term_change_pct=None,
        funding_rate=-0.05,
        oi_change_pct=18.0,
        price_change_threshold_pct=8.0,
        short_term_breakout_threshold_pct=2.5,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        oi_surge_threshold_pct=12.0,
        price_flat_threshold_pct=2.5,
        funding_negative_threshold_pct=-0.03,
    )
    event_keys = {event.event_key for event in events}
    assert "price_surge_up" in event_keys
    assert "funding_negative" in event_keys


def test_detect_subscription_events_detects_oversold() -> None:
    close_prices = [100.0 - index for index in range(40)]
    events = detect_subscription_events(
        symbol="ETH",
        close_prices=close_prices,
        change_24h=-3.0,
        short_term_change_pct=None,
        funding_rate=None,
        oi_change_pct=None,
        price_change_threshold_pct=8.0,
        short_term_breakout_threshold_pct=2.5,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        oi_surge_threshold_pct=12.0,
        price_flat_threshold_pct=2.5,
        funding_negative_threshold_pct=-0.03,
    )
    event_keys = {event.event_key for event in events}
    assert "rsi_oversold" in event_keys


def test_detect_subscription_events_detects_short_term_breakout() -> None:
    events = detect_subscription_events(
        symbol="SOL",
        close_prices=[100.0] * 40,
        change_24h=1.0,
        short_term_change_pct=3.2,
        funding_rate=None,
        oi_change_pct=None,
        price_change_threshold_pct=5.0,
        short_term_breakout_threshold_pct=2.5,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        oi_surge_threshold_pct=8.0,
        price_flat_threshold_pct=2.5,
        funding_negative_threshold_pct=-0.015,
    )

    event_keys = {event.event_key for event in events}
    assert "short_term_breakout_up" in event_keys
