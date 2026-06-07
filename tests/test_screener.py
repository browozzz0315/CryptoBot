from analysis.screener import top_gainers, top_losers, top_volume


def test_top_gainers_orders_descending() -> None:
    quotes = [
        {"symbol": "BTC", "price": 1, "change_24h": 1.0, "total_volume": 10},
        {"symbol": "ETH", "price": 1, "change_24h": 5.0, "total_volume": 9},
        {"symbol": "SOL", "price": 1, "change_24h": -2.0, "total_volume": 8},
    ]
    result = top_gainers(quotes, 2)
    assert [item["symbol"] for item in result] == ["ETH", "BTC"]


def test_top_losers_orders_ascending() -> None:
    quotes = [
        {"symbol": "BTC", "price": 1, "change_24h": 1.0, "total_volume": 10},
        {"symbol": "ETH", "price": 1, "change_24h": 5.0, "total_volume": 9},
        {"symbol": "SOL", "price": 1, "change_24h": -2.0, "total_volume": 8},
    ]
    result = top_losers(quotes, 2)
    assert [item["symbol"] for item in result] == ["SOL", "BTC"]


def test_top_volume_orders_descending() -> None:
    quotes = [
        {"symbol": "BTC", "price": 1, "change_24h": 1.0, "total_volume": 10},
        {"symbol": "ETH", "price": 1, "change_24h": 5.0, "total_volume": 90},
        {"symbol": "SOL", "price": 1, "change_24h": -2.0, "total_volume": 80},
    ]
    result = top_volume(quotes, 2)
    assert [item["symbol"] for item in result] == ["ETH", "SOL"]
