import asyncio
from datetime import UTC, datetime
from pathlib import Path

from storage.database import create_engine, create_session_factory, init_database
from storage.subscription_events import (
    SubscriptionEventStateRecord,
    SubscriptionEventStateRepository,
)


async def _run_recent_state_checks() -> None:
    db_path = Path("runtime/test_subscription_event_repository.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_engine("sqlite+aiosqlite:///./runtime/test_subscription_event_repository.db")
    session_factory = create_session_factory(engine)
    await init_database(engine)

    repo = SubscriptionEventStateRepository(session_factory)
    await repo.upsert_state(
        SubscriptionEventStateRecord(
            chat_id="123",
            symbol="BTC",
            event_key="price_surge_up",
            last_event_value=6.0,
            last_triggered_at=datetime(2026, 6, 19, 10, 0, tzinfo=UTC),
        )
    )
    await repo.upsert_state(
        SubscriptionEventStateRecord(
            chat_id="123",
            symbol="ETH",
            event_key="funding_negative",
            last_event_value=-0.02,
            last_triggered_at=datetime(2026, 6, 19, 11, 0, tzinfo=UTC),
        )
    )

    recent = await repo.list_recent_states(chat_id="123")
    assert [state.symbol for state in recent] == ["ETH", "BTC"]

    btc_recent = await repo.list_recent_states(chat_id="123", symbols=["BTC"])
    assert [state.symbol for state in btc_recent] == ["BTC"]
    assert btc_recent[0].event_key == "price_surge_up"

    await engine.dispose()
    if db_path.exists():
        db_path.unlink()


def test_list_recent_states_orders_by_last_triggered_at_and_filters_symbol() -> None:
    asyncio.run(_run_recent_state_checks())
