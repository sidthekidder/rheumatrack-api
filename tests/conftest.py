"""Shared pytest fixtures.

Each test runs in its own event loop (pytest-asyncio default). The
SQLAlchemy async engine is module-level (`app.database.engine`), so its
asyncpg connections become bound to the loop of the first test that
uses them. Subsequent tests on a new loop hit
`got Future ... attached to a different loop`. We dispose the engine
after every test so the next test starts with a fresh pool on its own
loop.
"""
import pytest

from app.database import engine


@pytest.fixture(autouse=True)
async def _dispose_engine_per_test():
    yield
    await engine.dispose()
