import os
import tempfile
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.base import get_engine, get_session_factory, reset_engine_for_tests
from app.db.session import get_db
from app.models import Base
from app.providers.bundle import build_mock_providers
from app.routers import simulator, webhook_whatsapp
from app.services import rate_limit_service


@pytest_asyncio.fixture
async def app_client():
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    reset_engine_for_tests()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.main import app

    session_factory = get_session_factory()

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    providers = build_mock_providers()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[webhook_whatsapp.get_providers] = lambda: providers
    app.dependency_overrides[simulator.get_providers] = lambda: providers

    rate_limit_service.reset_rate_limiter_for_tests()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, providers

    app.dependency_overrides.clear()
    await engine.dispose()
    reset_engine_for_tests()
    rate_limit_service.reset_rate_limiter_for_tests()
