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
        assert "可用幣種" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported symbol")
