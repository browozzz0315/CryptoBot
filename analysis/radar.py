from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RadarEntry:
    symbol: str
    market_cap: float
    change_24h: float
    total_volume: float
    funding_rate: float | None
    oi_change_pct: float | None
    long_short_ratio: float | None
    sideways_days: int
    trending: bool


def build_heat_rank(entries: list[RadarEntry], limit: int) -> list[RadarEntry]:
    return sorted(entries, key=_heat_score, reverse=True)[:limit]


def build_long_rank(entries: list[RadarEntry], limit: int) -> list[RadarEntry]:
    eligible = [entry for entry in entries if entry.funding_rate is not None]
    return sorted(eligible, key=_long_score, reverse=True)[:limit]


def build_composite_rank(entries: list[RadarEntry], limit: int) -> list[tuple[RadarEntry, int]]:
    ranked = sorted(entries, key=lambda item: _composite_score(item), reverse=True)[:limit]
    return [(entry, _composite_score(entry)) for entry in ranked]


def build_ambush_rank(entries: list[RadarEntry], limit: int) -> list[tuple[RadarEntry, int]]:
    ranked = sorted(entries, key=lambda item: _ambush_score(item), reverse=True)[:limit]
    return [(entry, _ambush_score(entry)) for entry in ranked]


def build_highlights(
    *,
    heat_entries: list[RadarEntry],
    long_entries: list[RadarEntry],
    composite_entries: list[tuple[RadarEntry, int]],
    ambush_entries: list[tuple[RadarEntry, int]],
) -> list[str]:
    lines: list[str] = []

    for entry in heat_entries[:3]:
        if entry.trending and entry.sideways_days >= 20:
            lines.append(
                f"🔥💤 {entry.symbol} 熱度上升且已橫盤 {entry.sideways_days} 天，可觀察是否帶動 OI。"
            )
        elif (entry.oi_change_pct or 0) >= 15:
            lines.append(f"🔥⚡ {entry.symbol} 熱度與 OI 同步升溫，OI {entry.oi_change_pct:+.0f}%。")

    for entry in long_entries[:2]:
        if entry.funding_rate is not None and entry.funding_rate < 0:
            lines.append(f"🔥 {entry.symbol} 費率 {entry.funding_rate:+.3f}% 偏負，可留意逆勢反彈。")

    composite_symbols = {entry.symbol for entry, _ in composite_entries[:3]}
    for entry, score in ambush_entries[:3]:
        prefix = "⭐" if entry.symbol in composite_symbols else "🎯"
        lines.append(
            f"{prefix} {entry.symbol} 綜合分 {score}，市值約 ${entry.market_cap/1_000_000:.0f}M，橫盤 {entry.sideways_days} 天。"
        )

    return lines[:8]


def estimate_sideways_days(
    close_prices: list[float],
    *,
    threshold_pct: float,
    candles_per_day: int = 6,
) -> int:
    if len(close_prices) < candles_per_day:
        return 0

    lookback = min(len(close_prices), candles_per_day * 60)
    relevant = close_prices[-lookback:]
    high = max(relevant)
    low = min(relevant)
    if low <= 0:
        return 0

    range_pct = ((high - low) / low) * 100
    if range_pct > threshold_pct:
        return 0
    return max(1, lookback // candles_per_day)


def calculate_oi_change_pct(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    previous = values[-2]
    current = values[-1]
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100


def _heat_score(entry: RadarEntry) -> float:
    score = 0.0
    score += 40 if entry.trending else 0
    score += min(max(entry.change_24h, -30), 150) * 0.3
    score += min(max(entry.oi_change_pct or 0, -50), 100) * 0.2
    score += min(entry.total_volume / 100_000_000, 30)
    return score


def _long_score(entry: RadarEntry) -> float:
    funding_component = 0.0
    if entry.funding_rate is not None:
        funding_component = max(-entry.funding_rate * 1000, 0)
    oi_component = max(entry.oi_change_pct or 0, -50)
    price_component = max(entry.change_24h, -30)
    return funding_component + (oi_component * 0.5) + (price_component * 0.4)


def _composite_score(entry: RadarEntry) -> int:
    market_cap_score = _scale_inverse(entry.market_cap, floor=5_000_000, ceiling=5_000_000_000, weight=25)
    funding_score = _scale_negative(entry.funding_rate, weight=25)
    sideways_score = min(entry.sideways_days, 180) / 180 * 25
    oi_score = _scale_positive(entry.oi_change_pct, weight=25)
    return round(market_cap_score + funding_score + sideways_score + oi_score)


def _ambush_score(entry: RadarEntry) -> int:
    market_cap_score = _scale_inverse(entry.market_cap, floor=5_000_000, ceiling=2_000_000_000, weight=35)
    oi_score = _scale_positive(entry.oi_change_pct, weight=30)
    sideways_score = min(entry.sideways_days, 180) / 180 * 20
    funding_score = _scale_negative(entry.funding_rate, weight=15)
    return round(market_cap_score + oi_score + sideways_score + funding_score)


def _scale_inverse(value: float, *, floor: float, ceiling: float, weight: float) -> float:
    clamped = min(max(value, floor), ceiling)
    normalized = 1 - ((clamped - floor) / (ceiling - floor))
    return normalized * weight


def _scale_positive(value: float | None, *, weight: float) -> float:
    if value is None:
        return 0.0
    clamped = min(max(value, -20), 50)
    normalized = (clamped + 20) / 70
    return normalized * weight


def _scale_negative(value: float | None, *, weight: float) -> float:
    if value is None:
        return 0.0
    clamped = min(max(value, -0.5), 0.1)
    normalized = (0.1 - clamped) / 0.6
    return normalized * weight
