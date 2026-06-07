from __future__ import annotations


def top_gainers(quotes: list[dict[str, float | str]], limit: int) -> list[dict[str, float | str]]:
    return sorted(quotes, key=lambda item: float(item["change_24h"]), reverse=True)[:limit]


def top_losers(quotes: list[dict[str, float | str]], limit: int) -> list[dict[str, float | str]]:
    return sorted(quotes, key=lambda item: float(item["change_24h"]))[:limit]


def top_volume(quotes: list[dict[str, float | str]], limit: int) -> list[dict[str, float | str]]:
    return sorted(quotes, key=lambda item: float(item["total_volume"]), reverse=True)[:limit]
