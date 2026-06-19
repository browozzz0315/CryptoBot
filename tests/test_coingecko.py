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
