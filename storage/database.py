from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from storage.models import Base


def _ensure_sqlite_parent_exists(database_url: str) -> None:
    sqlite_prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return

    raw_path = database_url.removeprefix(sqlite_prefix)
    if raw_path.startswith("./"):
        raw_path = raw_path[2:]

    db_path = Path(raw_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)


def create_engine(database_url: str) -> AsyncEngine:
    _ensure_sqlite_parent_exists(database_url)
    return create_async_engine(database_url, echo=False, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
