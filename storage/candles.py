from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from storage.models import Candle


@dataclass(slots=True)
class CandleRecord:
    symbol: str
    timeframe: str
    source: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float


class CandleRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_candles(self, candles: list[CandleRecord]) -> int:
        if not candles:
            return 0

        values = [
            {
                "symbol": candle.symbol,
                "timeframe": candle.timeframe,
                "source": candle.source,
                "open_time": candle.open_time,
                "close_time": candle.close_time,
                "open_price": candle.open_price,
                "high_price": candle.high_price,
                "low_price": candle.low_price,
                "close_price": candle.close_price,
            }
            for candle in candles
        ]

        statement = insert(Candle).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "close_time", "source"],
            set_={
                "open_time": statement.excluded.open_time,
                "open_price": statement.excluded.open_price,
                "high_price": statement.excluded.high_price,
                "low_price": statement.excluded.low_price,
                "close_price": statement.excluded.close_price,
            },
        )

        async with self._session_factory() as session:
            await session.execute(statement)
            await session.commit()

        return len(candles)

    async def list_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        source: str,
        limit: int = 100,
    ) -> list[Candle]:
        query = (
            select(Candle)
            .where(Candle.symbol == symbol.upper())
            .where(Candle.timeframe == timeframe)
            .where(Candle.source == source)
            .order_by(Candle.close_time.desc())
            .limit(limit)
        )

        async with self._session_factory() as session:
            result = await session.execute(query)
            return list(result.scalars().all())

    async def list_close_prices(
        self,
        *,
        symbol: str,
        timeframe: str,
        source: str,
        limit: int = 100,
    ) -> list[float]:
        candles = await self.list_candles(
            symbol=symbol,
            timeframe=timeframe,
            source=source,
            limit=limit,
        )
        candles = list(reversed(candles))
        return [candle.close_price for candle in candles]
