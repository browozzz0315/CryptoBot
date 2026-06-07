from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from storage.models import UserSubscription


@dataclass(slots=True)
class UserSubscriptionRecord:
    chat_id: str
    symbol: str


class UserSubscriptionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_subscription(self, subscription: UserSubscriptionRecord) -> UserSubscription:
        statement = insert(UserSubscription).values(
            chat_id=subscription.chat_id,
            symbol=subscription.symbol.upper(),
        )
        statement = statement.on_conflict_do_nothing(
            index_elements=["chat_id", "symbol"],
        )

        async with self._session_factory() as session:
            await session.execute(statement)
            await session.commit()

            query = (
                select(UserSubscription)
                .where(UserSubscription.chat_id == subscription.chat_id)
                .where(UserSubscription.symbol == subscription.symbol.upper())
            )
            result = await session.execute(query)
            return result.scalar_one()

    async def delete_subscription(self, *, chat_id: str, symbol: str) -> bool:
        async with self._session_factory() as session:
            statement = (
                delete(UserSubscription)
                .where(UserSubscription.chat_id == chat_id)
                .where(UserSubscription.symbol == symbol.upper())
            )
            result = await session.execute(statement)
            await session.commit()
            return bool(result.rowcount)

    async def list_subscriptions(self, *, chat_id: str) -> list[UserSubscription]:
        query = (
            select(UserSubscription)
            .where(UserSubscription.chat_id == chat_id)
            .order_by(UserSubscription.symbol.asc())
        )
        async with self._session_factory() as session:
            result = await session.execute(query)
            return list(result.scalars().all())

    async def list_all_subscriptions(self) -> list[UserSubscription]:
        query = select(UserSubscription).order_by(UserSubscription.chat_id.asc(), UserSubscription.symbol.asc())
        async with self._session_factory() as session:
            result = await session.execute(query)
            return list(result.scalars().all())
