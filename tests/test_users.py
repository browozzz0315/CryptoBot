import asyncio
from pathlib import Path

from storage.database import create_engine, create_session_factory, init_database
from storage.users import UserSubscriptionRecord, UserSubscriptionRepository


async def _run_user_subscription_checks() -> None:
    db_path = Path("runtime/test_users.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_engine("sqlite+aiosqlite:///./runtime/test_users.db")
    session_factory = create_session_factory(engine)
    await init_database(engine)

    repo = UserSubscriptionRepository(session_factory)
    await repo.upsert_subscription(UserSubscriptionRecord(chat_id="1", symbol="BTC"))
    await repo.upsert_subscription(UserSubscriptionRecord(chat_id="1", symbol="ETH"))
    subscriptions = await repo.list_subscriptions(chat_id="1")
    assert [item.symbol for item in subscriptions] == ["BTC", "ETH"]

    deleted = await repo.delete_subscription(chat_id="1", symbol="ETH")
    assert deleted is True
    subscriptions = await repo.list_subscriptions(chat_id="1")
    assert [item.symbol for item in subscriptions] == ["BTC"]

    await engine.dispose()
    if db_path.exists():
        db_path.unlink()


def test_user_subscription_repository_crud() -> None:
    asyncio.run(_run_user_subscription_checks())
