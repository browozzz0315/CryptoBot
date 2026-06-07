from datetime import UTC, datetime, timedelta
from pathlib import Path

from charts.candlestick import render_price_chart
from storage.models import Candle


def test_render_price_chart_outputs_file() -> None:
    output_dir = Path("runtime/charts_test")
    candles = []
    base_time = datetime(2026, 6, 1, tzinfo=UTC)
    for index in range(10):
        close_time = base_time + timedelta(hours=4 * index)
        candles.append(
            Candle(
                symbol="BTC",
                timeframe="4h",
                source="test",
                open_time=close_time - timedelta(hours=4),
                close_time=close_time,
                open_price=100 + index,
                high_price=102 + index,
                low_price=99 + index,
                close_price=101 + index,
            )
        )

    chart_path = render_price_chart(symbol="BTC", candles=candles, output_dir=str(output_dir))
    assert chart_path.exists()
    chart_path.unlink()
    output_dir.rmdir()
