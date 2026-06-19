from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from loguru import logger

from data.base import retry_on_request_error


SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "TRX": "tron",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "TON": "the-open-network",
    "DOT": "polkadot",
    "MATIC": "polygon-ecosystem-token",
    "POL": "polygon-ecosystem-token",
    "SUI": "sui",
}

SYMBOL_ALIASES = {
    "XBT": "BTC",
    "BTCUSDT": "BTC",
    "BTCUSD": "BTC",
    "BTCUSDC": "BTC",
    "ETHUSDT": "ETH",
    "ETHUSD": "ETH",
    "ETHUSDC": "ETH",
    "SOLUSDT": "SOL",
    "SOLUSD": "SOL",
    "BNBUSDT": "BNB",
    "BNBUSD": "BNB",
}


@dataclass(slots=True)
class CoinGeckoClient:
    base_url: str
    api_key: str | None
    api_plan: str = "demo"
    quote_currency: str = "usd"
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.api_plan = self.api_plan.lower()
        if self.api_plan not in {"demo", "pro"}:
            raise ValueError("COINGECKO_API_PLAN must be either 'demo' or 'pro'.")

        headers = {}
        if self.api_key:
            header_name = "x-cg-pro-api-key" if self.api_plan == "pro" else "x-cg-demo-api-key"
            headers[header_name] = self.api_key

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0),
            headers=headers,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry_on_request_error
    async def get_price(self, symbol: str) -> dict[str, float | str | datetime]:
        normalized_symbol = self.normalize_symbol(symbol)
        coin_id = self._resolve_coin_id(normalized_symbol)
        response = await self._client.get(
            "/coins/markets",
            params={
                "vs_currency": self.quote_currency,
                "ids": coin_id,
                "price_change_percentage": "24h",
            },
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict):
            self._raise_payload_error(
                symbol=normalized_symbol,
                coin_id=coin_id,
                status_code=response.status_code,
                payload=payload,
            )

        if not isinstance(payload, list):
            raise ValueError(
                "CoinGecko returned an unexpected markets payload. "
                f"symbol={normalized_symbol}, coin_id={coin_id}, plan={self.api_plan}, "
                f"base_url={self.base_url}, status_code={response.status_code}, "
                f"payload_type={type(payload).__name__}"
            )

        if not payload:
            raise ValueError(
                "CoinGecko returned an empty markets payload. "
                f"symbol={normalized_symbol}, coin_id={coin_id}, plan={self.api_plan}, "
                f"base_url={self.base_url}, status_code={response.status_code}"
            )

        coin_data = payload[0]
        price = coin_data.get("current_price")
        if price is None:
            raise ValueError(
                "CoinGecko markets payload is missing current_price. "
                f"symbol={normalized_symbol}, coin_id={coin_id}, plan={self.api_plan}, "
                f"base_url={self.base_url}"
            )

        last_updated = coin_data.get("last_updated")
        last_updated_at = (
            datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            if isinstance(last_updated, str)
            else datetime.now(tz=UTC)
        )

        return {
            "symbol": normalized_symbol,
            "name": str(coin_data.get("name", normalized_symbol)),
            "price": float(price),
            "change_24h": float(coin_data.get("price_change_percentage_24h") or 0.0),
            "market_cap": float(coin_data.get("market_cap") or 0.0),
            "total_volume": float(coin_data.get("total_volume") or 0.0),
            "high_24h": float(coin_data.get("high_24h") or 0.0),
            "low_24h": float(coin_data.get("low_24h") or 0.0),
            "last_updated_at": last_updated_at,
        }

    async def get_prices(self, symbols: list[str]) -> list[dict[str, float | str | datetime]]:
        quotes = []
        for symbol in symbols:
            quote = await self.get_price(symbol)
            quotes.append(quote)
        return quotes

    @retry_on_request_error
    async def get_trending_symbols(self) -> list[str]:
        response = await self._client.get("/search/trending")
        response.raise_for_status()
        payload = response.json()
        symbols: list[str] = []
        for item in payload.get("coins", []):
            coin_item = item.get("item", {})
            symbol = str(coin_item.get("symbol", "")).upper()
            if symbol:
                symbols.append(symbol)
        return symbols

    @retry_on_request_error
    async def search_symbol(self, query: str) -> list[dict[str, str]]:
        response = await self._client.get("/search", params={"query": query})
        response.raise_for_status()
        payload = response.json()
        return [
            {
                "id": str(item.get("id", "")),
                "symbol": str(item.get("symbol", "")).upper(),
                "name": str(item.get("name", "")),
            }
            for item in payload.get("coins", [])
        ]

    @retry_on_request_error
    async def get_ohlc(self, symbol: str, days: int) -> list[dict[str, float | str | datetime]]:
        normalized_symbol = self.normalize_symbol(symbol)
        coin_id = self._resolve_coin_id(normalized_symbol)
        timeframe, interval_seconds = self._resolve_ohlc_granularity(days)

        response = await self._client.get(
            f"/coins/{coin_id}/ohlc",
            params={
                "vs_currency": self.quote_currency,
                "days": days,
            },
        )
        response.raise_for_status()
        payload = response.json()

        candles = []
        for row in payload:
            close_time = datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC)
            open_time = datetime.fromtimestamp(
                (int(row[0]) / 1000) - interval_seconds,
                tz=UTC,
            )
            candles.append(
                {
                    "symbol": normalized_symbol,
                    "timeframe": timeframe,
                    "source": "coingecko",
                    "open_time": open_time,
                    "close_time": close_time,
                    "open_price": float(row[1]),
                    "high_price": float(row[2]),
                    "low_price": float(row[3]),
                    "close_price": float(row[4]),
                }
            )

        return candles

    def _resolve_coin_id(self, symbol: str) -> str:
        if symbol not in SYMBOL_TO_COINGECKO_ID:
            raise ValueError(
                f"目前未支援 {symbol}。可用幣種：{', '.join(self.supported_symbols())}"
            )
        return SYMBOL_TO_COINGECKO_ID[symbol]

    def normalize_symbol(self, raw_symbol: str) -> str:
        symbol = raw_symbol.strip().upper()
        if not symbol:
            raise ValueError("請提供幣種代號，例如：/price BTC")

        alias_symbol = SYMBOL_ALIASES.get(symbol, symbol)
        for suffix in ("USDT", "USD", "USDC"):
            if alias_symbol.endswith(suffix) and len(alias_symbol) > len(suffix):
                alias_symbol = alias_symbol[: -len(suffix)]
                break

        return SYMBOL_ALIASES.get(alias_symbol, alias_symbol)

    def validate_symbol(self, raw_symbol: str) -> str:
        normalized_symbol = self.normalize_symbol(raw_symbol)
        self._resolve_coin_id(normalized_symbol)
        return normalized_symbol

    def is_supported_symbol(self, raw_symbol: str) -> bool:
        try:
            self.validate_symbol(raw_symbol)
        except ValueError:
            return False
        return True

    def supported_symbols(self) -> list[str]:
        return sorted(SYMBOL_TO_COINGECKO_ID.keys())

    def _resolve_ohlc_granularity(self, days: int) -> tuple[str, int]:
        if days in (1, 2):
            return ("30m", 30 * 60)
        if days in (7, 14, 30):
            return ("4h", 4 * 60 * 60)
        if days in (90, 180, 365):
            return ("4d", 4 * 24 * 60 * 60)
        raise ValueError("CoinGecko OHLC days 僅支援 1, 2, 7, 14, 30, 90, 180, 365")

    def _raise_payload_error(
        self,
        *,
        symbol: str,
        coin_id: str,
        status_code: int,
        payload: dict,
    ) -> None:
        error_message = payload.get("error") or payload.get("message")
        status = payload.get("status")
        if isinstance(status, dict):
            error_message = (
                error_message
                or status.get("error_message")
                or status.get("message")
                or status.get("error_code")
            )

        logger.warning(
            "CoinGecko returned an error payload. symbol={}, coin_id={}, plan={}, "
            "base_url={}, status_code={}, payload_keys={}",
            symbol,
            coin_id,
            self.api_plan,
            self.base_url,
            status_code,
            sorted(str(key) for key in payload.keys()),
        )
        raise ValueError(
            "CoinGecko returned an error payload. "
            f"symbol={symbol}, coin_id={coin_id}, plan={self.api_plan}, "
            f"base_url={self.base_url}, status_code={status_code}, "
            f"message={error_message or 'N/A'}"
        )
