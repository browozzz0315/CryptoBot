import asyncio
from pathlib import Path

from storage.alerts import AlertRepository, PriceAlertRecord
from storage.database import create_engine, create_session_factory, init_database


async def _run_alert_repo_checks() -> None:
    db_path = Path("runtime/test_alerts.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_engine("sqlite+aiosqlite:///./runtime/test_alerts.db")
    session_factory = create_session_factory(engine)
    await init_database(engine)

    repo = AlertRepository(session_factory)
    created = await repo.create_alert(
        PriceAlertRecord(chat_id="123", symbol="BTC", direction="above", target_price=70000)
    )
    alerts = await repo.list_alerts(chat_id="123")
    assert len(alerts) == 1
    assert created.id == alerts[0].id

    deleted = await repo.delete_alert(chat_id="123", alert_id=created.id)
    assert deleted is True
    alerts = await repo.list_alerts(chat_id="123")
    assert alerts == []

    await engine.dispose()
    if db_path.exists():
        db_path.unlink()


def test_alert_repository_crud() -> None:
    asyncio.run(_run_alert_repo_checks())
