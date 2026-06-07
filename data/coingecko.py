from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

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
    "MATIC": "matic-network",
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
    quote_currency: str = "usd"
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        headers = {}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key

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

        if not payload:
            raise ValueError(f"CoinGecko 找不到幣種：{normalized_symbol}")

        coin_data = payload[0]
        price = coin_data.get("current_price")
        if price is None:
            raise ValueError(f"CoinGecko 回傳資料缺少價格欄位：{normalized_symbol}")

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

    def supported_symbols(self) -> list[str]:
        return sorted(SYMBOL_TO_COINGECKO_ID.keys())
