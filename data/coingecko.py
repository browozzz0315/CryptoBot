from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from data.base import retry_on_request_error


SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
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
    async def get_price(self, symbol: str) -> dict[str, float]:
        coin_id = self._resolve_coin_id(symbol)
        response = await self._client.get(
            "/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": self.quote_currency,
                "include_24hr_change": "true",
            },
        )
        response.raise_for_status()
        payload = response.json()

        if coin_id not in payload:
            raise ValueError(f"CoinGecko 找不到幣種：{symbol}")

        coin_data = payload[coin_id]
        price = coin_data.get(self.quote_currency)
        change_key = f"{self.quote_currency}_24h_change"
        change_24h = coin_data.get(change_key)

        if price is None:
            raise ValueError(f"CoinGecko 回傳資料缺少價格欄位：{symbol}")

        return {
            "price": float(price),
            "change_24h": float(change_24h) if change_24h is not None else 0.0,
        }

    async def get_prices(self, symbols: list[str]) -> list[dict[str, float | str]]:
        quotes = []
        for symbol in symbols:
            quote = await self.get_price(symbol)
            quotes.append(
                {
                    "symbol": symbol.upper(),
                    "price": quote["price"],
                    "change_24h": quote["change_24h"],
                }
            )
        return quotes

    def _resolve_coin_id(self, symbol: str) -> str:
        normalized_symbol = symbol.upper()
        if normalized_symbol not in SYMBOL_TO_COINGECKO_ID:
            raise ValueError(
                f"目前未設定 {normalized_symbol} 的 CoinGecko 映射，請先補到 SYMBOL_TO_COINGECKO_ID。"
            )
        return SYMBOL_TO_COINGECKO_ID[normalized_symbol]
