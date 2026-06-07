from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from storage.models import PriceAlert


@dataclass(slots=True)
class PriceAlertRecord:
    chat_id: str
    symbol: str
    direction: str
    target_price: float


class AlertRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_alert(self, alert: PriceAlertRecord) -> PriceAlert:
        model = PriceAlert(
            chat_id=alert.chat_id,
            symbol=alert.symbol.upper(),
            direction=alert.direction.lower(),
            target_price=alert.target_price,
            is_active=True,
        )
        async with self._session_factory() as session:
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model

    async def list_alerts(self, *, chat_id: str, active_only: bool = True) -> list[PriceAlert]:
        query = select(PriceAlert).where(PriceAlert.chat_id == chat_id)
        if active_only:
            query = query.where(PriceAlert.is_active.is_(True))
        query = query.order_by(PriceAlert.created_at.desc())

        async with self._session_factory() as session:
            result = await session.execute(query)
            return list(result.scalars().all())

    async def delete_alert(self, *, chat_id: str, alert_id: int) -> bool:
        async with self._session_factory() as session:
            query = (
                update(PriceAlert)
                .where(PriceAlert.id == alert_id)
                .where(PriceAlert.chat_id == chat_id)
                .where(PriceAlert.is_active.is_(True))
                .values(is_active=False, updated_at=datetime.now(tz=UTC))
            )
            result = await session.execute(query)
            await session.commit()
            return bool(result.rowcount)

    async def list_active_alerts(self) -> list[PriceAlert]:
        query = select(PriceAlert).where(PriceAlert.is_active.is_(True)).order_by(PriceAlert.created_at.asc())
        async with self._session_factory() as session:
            result = await session.execute(query)
            return list(result.scalars().all())

    async def mark_triggered(self, alert_id: int) -> None:
        async with self._session_factory() as session:
            query = (
                update(PriceAlert)
                .where(PriceAlert.id == alert_id)
                .values(
                    is_active=False,
                    triggered_at=datetime.now(tz=UTC),
                    updated_at=datetime.now(tz=UTC),
                )
            )
            await session.execute(query)
            await session.commit()
