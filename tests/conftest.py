import os
import tempfile
from pathlib import Path

import pytest_asyncio

os.environ.setdefault("APP_ENV", "test")


@pytest_asyncio.fixture
async def db_session():
    """Isolated temp-file SQLite DB per test, with all tables created fresh."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

    from app.db.base import get_session_factory, reset_engine_for_tests
    from app.models import Base

    reset_engine_for_tests()
    from app.db.base import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session

    await engine.dispose()
    reset_engine_for_tests()
