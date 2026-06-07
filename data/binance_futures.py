from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from data.base import retry_on_request_error

BINANCE_SYMBOL_ALIASES = {
    "MATIC": "POLUSDT",
    "POL": "POLUSDT",
}


@dataclass(slots=True)
class BinanceFuturesClient:
    base_url: str
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def normalize_symbol(self, base_symbol: str) -> str:
        normalized = base_symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol 不可為空")
        if normalized in BINANCE_SYMBOL_ALIASES:
            return BINANCE_SYMBOL_ALIASES[normalized]
        if normalized.endswith("USDT"):
            return normalized
        return f"{normalized}USDT"

    @retry_on_request_error
    async def get_latest_funding_rate(self, base_symbol: str) -> dict[str, float | datetime | str]:
        symbol = self.normalize_symbol(base_symbol)
        response = await self._client.get(
            "/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": 1},
        )
        response.raise_for_status()
        payload = response.json()
        if not payload:
            raise ValueError(f"Binance funding rate 找不到資料：{symbol}")
        item = payload[-1]
        return {
            "symbol": symbol,
            "funding_rate": float(item["fundingRate"]),
            "mark_price": float(item["markPrice"]),
            "funding_time": datetime.fromtimestamp(int(item["fundingTime"]) / 1000, tz=UTC),
        }

    @retry_on_request_error
    async def get_open_interest_hist(
        self,
        base_symbol: str,
        *,
        period: str = "1d",
        limit: int = 2,
    ) -> list[dict[str, float | datetime | str]]:
        symbol = self.normalize_symbol(base_symbol)
        response = await self._client.get(
            "/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        response.raise_for_status()
        payload = response.json()
        result = []
        for item in payload:
            result.append(
                {
                    "symbol": item["symbol"],
                    "open_interest": float(item["sumOpenInterest"]),
                    "open_interest_value": float(item["sumOpenInterestValue"]),
                    "timestamp": datetime.fromtimestamp(int(item["timestamp"]) / 1000, tz=UTC),
                }
            )
        return result

    @retry_on_request_error
    async def get_top_long_short_ratio(
        self,
        base_symbol: str,
        *,
        period: str = "1d",
        limit: int = 1,
    ) -> dict[str, float | datetime | str]:
        symbol = self.normalize_symbol(base_symbol)
        response = await self._client.get(
            "/futures/data/topLongShortPositionRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        response.raise_for_status()
        payload = response.json()
        if not payload:
            raise ValueError(f"Binance top long/short ratio 找不到資料：{symbol}")
        item = payload[-1]
        return {
            "symbol": item["symbol"],
            "long_short_ratio": float(item["longShortRatio"]),
            "long_account": float(item["longAccount"]),
            "short_account": float(item["shortAccount"]),
            "timestamp": datetime.fromtimestamp(int(item["timestamp"]) / 1000, tz=UTC),
        }
