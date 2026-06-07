from analysis.radar import (
    RadarEntry,
    build_ambush_rank,
    build_composite_rank,
    build_heat_rank,
    build_highlights,
    build_long_rank,
    calculate_oi_change_pct,
    estimate_sideways_days,
)


def _entry(symbol: str, **kwargs) -> RadarEntry:
    base = {
        "market_cap": 10_000_000.0,
        "change_24h": 5.0,
        "total_volume": 50_000_000.0,
        "funding_rate": -0.05,
        "oi_change_pct": 10.0,
        "long_short_ratio": 1.2,
        "sideways_days": 30,
        "trending": False,
    }
    base.update(kwargs)
    return RadarEntry(symbol=symbol, **base)


def test_calculate_oi_change_pct() -> None:
    assert round(calculate_oi_change_pct([100, 120]) or 0, 2) == 20.0


def test_estimate_sideways_days() -> None:
    close_prices = [100, 101, 100.5, 99.8, 100.2, 100.1] * 5
    assert estimate_sideways_days(close_prices, threshold_pct=5.0) > 0


def test_radar_rankings_return_expected_shapes() -> None:
    entries = [
        _entry("AAA", trending=True, oi_change_pct=20.0),
        _entry("BBB", funding_rate=-0.2, change_24h=12.0),
        _entry("CCC", market_cap=5_000_000.0, sideways_days=90),
    ]
    assert build_heat_rank(entries, 2)
    assert build_long_rank(entries, 2)
    assert build_composite_rank(entries, 2)
    assert build_ambush_rank(entries, 2)


def test_highlights_are_generated() -> None:
    heat = [_entry("AAA", trending=True, sideways_days=40)]
    long_rank = [_entry("BBB", funding_rate=-0.2)]
    composite = [(_entry("CCC"), 88)]
    ambush = [(_entry("DDD"), 85)]
    highlights = build_highlights(
        heat_entries=heat,
        long_entries=long_rank,
        composite_entries=composite,
        ambush_entries=ambush,
    )
    assert highlights
