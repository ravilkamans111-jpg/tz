import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://payments:payments@localhost:5433/payments_test")
os.environ.setdefault("API_KEY", "test-key")

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db import Base, get_session
from app.main import app

HEADERS = {"X-API-Key": settings.api_key}


@pytest.fixture
async def engine():
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def client(session_factory):
    async def override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=HEADERS) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def count(session_factory):
    async def _count(table: str) -> int:
        async with session_factory() as session:
            return await session.scalar(text(f"select count(*) from {table}"))

    return _count
