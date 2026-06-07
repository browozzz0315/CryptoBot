from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from storage.models import SubscriptionEventState


@dataclass(slots=True)
class SubscriptionEventStateRecord:
    chat_id: str
    symbol: str
    event_key: str
    last_event_value: float | None
    last_triggered_at: datetime


class SubscriptionEventStateRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def is_in_cooldown(
        self,
        *,
        chat_id: str,
        symbol: str,
        event_key: str,
        cooldown_minutes: int,
        now: datetime | None = None,
    ) -> bool:
        state = await self.get_state(chat_id=chat_id, symbol=symbol, event_key=event_key)
        if state is None or state.last_triggered_at is None:
            return False

        reference_time = now or datetime.now(tz=UTC)
        last_triggered_at = self._ensure_utc_datetime(state.last_triggered_at)
        cooldown_until = last_triggered_at + timedelta(minutes=cooldown_minutes)
        return reference_time < cooldown_until

    async def get_state(
        self,
        *,
        chat_id: str,
        symbol: str,
        event_key: str,
    ) -> SubscriptionEventState | None:
        query = (
            select(SubscriptionEventState)
            .where(SubscriptionEventState.chat_id == chat_id)
            .where(SubscriptionEventState.symbol == symbol.upper())
            .where(SubscriptionEventState.event_key == event_key)
        )
        async with self._session_factory() as session:
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def upsert_state(self, state: SubscriptionEventStateRecord) -> None:
        statement = insert(SubscriptionEventState).values(
            chat_id=state.chat_id,
            symbol=state.symbol.upper(),
            event_key=state.event_key,
            last_event_value=state.last_event_value,
            last_triggered_at=state.last_triggered_at,
            created_at=state.last_triggered_at,
            updated_at=state.last_triggered_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["chat_id", "symbol", "event_key"],
            set_={
                "last_event_value": state.last_event_value,
                "last_triggered_at": state.last_triggered_at,
                "updated_at": state.last_triggered_at,
            },
        )

        async with self._session_factory() as session:
            await session.execute(statement)
            await session.commit()

    def _ensure_utc_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
