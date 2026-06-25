import asyncio

import httpx

from data.coingecko import CoinGeckoClient


def test_normalize_symbol_supports_pairs() -> None:
    client = CoinGeckoClient(base_url="https://api.coingecko.com/api/v3", api_key=None)
    assert client.normalize_symbol("btcusdt") == "BTC"
    assert client.normalize_symbol("xbt") == "BTC"


def test_supported_symbol_error_message() -> None:
    client = CoinGeckoClient(base_url="https://api.coingecko.com/api/v3", api_key=None)
    try:
        client._resolve_coin_id("UNKNOWN")
    except ValueError as exc:
        assert "目前未支援 UNKNOWN" in str(exc)
        assert "可用幣種" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported symbol")


def test_empty_markets_payload_message_contains_safe_context() -> None:
    async def run_case() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[])

        client = CoinGeckoClient(
            base_url="https://api.coingecko.com/api/v3",
            api_key="secret-test-key",
            api_plan="demo",
        )
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url=client.base_url,
            transport=httpx.MockTransport(handler),
        )

        try:
            await client.get_price("BTC")
        except ValueError as exc:
            message = str(exc)
            assert "symbol=BTC" in message
            assert "coin_id=bitcoin" in message
            assert "plan=demo" in message
            assert "secret-test-key" not in message
        else:
            raise AssertionError("Expected ValueError for empty CoinGecko payload")
        finally:
            await client.aclose()

    asyncio.run(run_case())


def test_get_market_quotes_formats_markets_payload() -> None:
    async def run_case() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v3/coins/markets"
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "abc",
                        "name": "ABC",
                        "current_price": 1.25,
                        "price_change_percentage_24h": 12.5,
                        "market_cap": 50_000_000,
                        "total_volume": 20_000_000,
                        "high_24h": 1.3,
                        "low_24h": 1.0,
                        "last_updated": "2026-06-25T00:00:00.000Z",
                    }
                ],
            )

        client = CoinGeckoClient(base_url="https://api.coingecko.com/api/v3", api_key=None)
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url=client.base_url,
            transport=httpx.MockTransport(handler),
        )

        try:
            quotes = await client.get_market_quotes(order="volume_desc", per_page=10)
        finally:
            await client.aclose()

        assert quotes[0]["symbol"] == "ABC"
        assert quotes[0]["market_cap"] == 50_000_000
        assert quotes[0]["change_24h"] == 12.5

    asyncio.run(run_case())
