from __future__ import annotations

from dataclasses import dataclass

from analysis.indicators import macd, rsi


@dataclass(slots=True)
class SubscriptionEvent:
    event_key: str
    title: str
    summary: str
    value: float | None = None
    severity: str = "low"
    score: int = 0
    reasons: list[str] | None = None


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


def detect_subscription_events(
    *,
    symbol: str,
    close_prices: list[float],
    change_24h: float,
    short_term_change_pct: float | None,
    funding_rate: float | None,
    oi_change_pct: float | None,
    price_change_threshold_pct: float,
    short_term_breakout_threshold_pct: float,
    rsi_overbought: float,
    rsi_oversold: float,
    oi_surge_threshold_pct: float,
    price_flat_threshold_pct: float,
    funding_negative_threshold_pct: float,
    min_confirmations: int = 2,
) -> list[SubscriptionEvent]:
    snapshot = build_indicator_snapshot(close_prices)
    latest_rsi = snapshot.get("rsi")
    macd_cross = detect_macd_cross(close_prices)
    confirmations = _build_confirmations(
        change_24h=change_24h,
        short_term_change_pct=short_term_change_pct,
        funding_rate=funding_rate,
        oi_change_pct=oi_change_pct,
        latest_rsi=latest_rsi,
        macd_cross=macd_cross,
        price_change_threshold_pct=price_change_threshold_pct,
        short_term_breakout_threshold_pct=short_term_breakout_threshold_pct,
        rsi_overbought=rsi_overbought,
        rsi_oversold=rsi_oversold,
        oi_surge_threshold_pct=oi_surge_threshold_pct,
        funding_negative_threshold_pct=funding_negative_threshold_pct,
    )
    events: list[SubscriptionEvent] = []

    if change_24h >= price_change_threshold_pct:
        events.append(
            _build_event(
                symbol=symbol,
                event_key="price_surge_up",
                title=f"{symbol} 急漲突破",
                summary=f"24h 漲幅 {change_24h:+.2f}%，已超過 {price_change_threshold_pct:.2f}% 閾值。",
                value=change_24h,
                primary_reason="price_up",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )
    elif change_24h <= -price_change_threshold_pct:
        events.append(
            _build_event(
                symbol=symbol,
                event_key="price_surge_down",
                title=f"{symbol} 急跌警示",
                summary=f"24h 跌幅 {change_24h:+.2f}%，已超過 {price_change_threshold_pct:.2f}% 閾值。",
                value=change_24h,
                primary_reason="price_down",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )

    if short_term_change_pct is not None and short_term_change_pct >= short_term_breakout_threshold_pct:
        events.append(
            _build_event(
                symbol=symbol,
                event_key="short_term_breakout_up",
                title=f"{symbol} 短線突破",
                summary=f"近幾根 K 線漲幅 {short_term_change_pct:+.2f}%，已超過 {short_term_breakout_threshold_pct:.2f}% 閾值。",
                value=short_term_change_pct,
                primary_reason="short_up",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )
    elif short_term_change_pct is not None and short_term_change_pct <= -short_term_breakout_threshold_pct:
        events.append(
            _build_event(
                symbol=symbol,
                event_key="short_term_breakout_down",
                title=f"{symbol} 短線跌破",
                summary=f"近幾根 K 線跌幅 {short_term_change_pct:+.2f}%，已超過 {short_term_breakout_threshold_pct:.2f}% 閾值。",
                value=short_term_change_pct,
                primary_reason="short_down",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )

    if isinstance(latest_rsi, (int, float)):
        if latest_rsi >= rsi_overbought:
            events.append(
                _build_event(
                    symbol=symbol,
                    event_key="rsi_overbought",
                    title=f"{symbol} RSI 過熱",
                    summary=f"RSI(14) 目前為 {latest_rsi:.2f}，高於 {rsi_overbought:.2f}。",
                    value=float(latest_rsi),
                    primary_reason="rsi_overbought",
                    confirmations=confirmations,
                    min_confirmations=min_confirmations,
                )
            )
        elif latest_rsi <= rsi_oversold:
            events.append(
                _build_event(
                    symbol=symbol,
                    event_key="rsi_oversold",
                    title=f"{symbol} RSI 過冷",
                    summary=f"RSI(14) 目前為 {latest_rsi:.2f}，低於 {rsi_oversold:.2f}。",
                    value=float(latest_rsi),
                    primary_reason="rsi_oversold",
                    confirmations=confirmations,
                    min_confirmations=min_confirmations,
                )
            )

    if macd_cross == "bullish":
        events.append(
            _build_event(
                symbol=symbol,
                event_key="macd_bullish_cross",
                title=f"{symbol} MACD 黃金交叉",
                summary="最近一根 K 線可能出現 MACD 上穿 Signal。",
                value=None,
                primary_reason="macd_bullish",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )
    elif macd_cross == "bearish":
        events.append(
            _build_event(
                symbol=symbol,
                event_key="macd_bearish_cross",
                title=f"{symbol} MACD 死亡交叉",
                summary="最近一根 K 線可能出現 MACD 下穿 Signal。",
                value=None,
                primary_reason="macd_bearish",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )

    if oi_change_pct is not None and oi_change_pct >= oi_surge_threshold_pct and abs(change_24h) <= price_flat_threshold_pct:
        events.append(
            _build_event(
                symbol=symbol,
                event_key="oi_build_up",
                title=f"{symbol} OI 暗流增加",
                summary=f"OI 增加 {oi_change_pct:+.2f}%，但 24h 價格僅 {change_24h:+.2f}%，可能有倉位累積。",
                value=oi_change_pct,
                primary_reason="oi_build_up",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )

    if funding_rate is not None and funding_rate <= funding_negative_threshold_pct:
        events.append(
            _build_event(
                symbol=symbol,
                event_key="funding_negative",
                title=f"{symbol} Funding 偏負",
                summary=f"Funding Rate 目前 {funding_rate:+.3f}%，低於 {funding_negative_threshold_pct:+.3f}%。",
                value=funding_rate,
                primary_reason="funding_negative",
                confirmations=confirmations,
                min_confirmations=min_confirmations,
            )
        )

    return events


def should_push_event(event: SubscriptionEvent, *, min_push_severity: str) -> bool:
    return _severity_rank(event.severity) >= _severity_rank(min_push_severity)


def _build_event(
    *,
    symbol: str,
    event_key: str,
    title: str,
    summary: str,
    value: float | None,
    primary_reason: str,
    confirmations: set[str],
    min_confirmations: int,
) -> SubscriptionEvent:
    reasons = _event_reasons(primary_reason, confirmations)
    return SubscriptionEvent(
        event_key=event_key,
        title=title,
        summary=summary,
        value=value,
        severity=_resolve_severity(reasons, min_confirmations=min_confirmations),
        score=_score_reasons(reasons),
        reasons=reasons,
    )


def _build_confirmations(
    *,
    change_24h: float,
    short_term_change_pct: float | None,
    funding_rate: float | None,
    oi_change_pct: float | None,
    latest_rsi: float | None | str,
    macd_cross: str | None,
    price_change_threshold_pct: float,
    short_term_breakout_threshold_pct: float,
    rsi_overbought: float,
    rsi_oversold: float,
    oi_surge_threshold_pct: float,
    funding_negative_threshold_pct: float,
) -> set[str]:
    confirmations: set[str] = set()
    if change_24h >= price_change_threshold_pct:
        confirmations.add("price_up")
    if change_24h <= -price_change_threshold_pct:
        confirmations.add("price_down")
    if short_term_change_pct is not None and short_term_change_pct >= short_term_breakout_threshold_pct:
        confirmations.add("short_up")
    if short_term_change_pct is not None and short_term_change_pct <= -short_term_breakout_threshold_pct:
        confirmations.add("short_down")
    if oi_change_pct is not None and oi_change_pct >= oi_surge_threshold_pct:
        confirmations.add("oi_surge")
    if funding_rate is not None and funding_rate <= funding_negative_threshold_pct:
        confirmations.add("funding_negative")
    if isinstance(latest_rsi, (int, float)) and latest_rsi >= rsi_overbought:
        confirmations.add("rsi_overbought")
    if isinstance(latest_rsi, (int, float)) and latest_rsi <= rsi_oversold:
        confirmations.add("rsi_oversold")
    if macd_cross:
        confirmations.add(f"macd_{macd_cross}")
    return confirmations


def _event_reasons(primary: str, confirmations: set[str]) -> list[str]:
    reasons = [primary]
    for reason in sorted(confirmations):
        if reason != primary:
            reasons.append(reason)
    return reasons


def _resolve_severity(reasons: list[str], *, min_confirmations: int) -> str:
    if len(reasons) >= min_confirmations:
        return "high"
    if len(reasons) > 1:
        return "medium"
    return "low"


def _score_reasons(reasons: list[str]) -> int:
    return min(100, 35 + (len(reasons) * 20))


def _severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(severity.lower(), 3)


def _last_value(series: list[float | None]) -> float | None:
    for value in reversed(series):
        if value is not None:
            return value
    return None


def detect_macd_cross(close_prices: list[float]) -> str | None:
    macd_series = macd(close_prices)
    macd_line = macd_series["macd"]
    signal_line = macd_series["signal"]

    pairs: list[tuple[float, float]] = []
    for macd_value, signal_value in zip(macd_line, signal_line, strict=False):
        if macd_value is None or signal_value is None:
            continue
        pairs.append((macd_value, signal_value))

    if len(pairs) < 2:
        return None

    previous_macd, previous_signal = pairs[-2]
    latest_macd, latest_signal = pairs[-1]
    if previous_macd < previous_signal and latest_macd >= latest_signal:
        return "bullish"
    if previous_macd > previous_signal and latest_macd <= latest_signal:
        return "bearish"
    return None
