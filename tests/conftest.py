import os
import tempfile
from pathlib import Path

import pytest_asyncio

os.environ.setdefault("APP_ENV", "test")

# Force every provider credential to "" for the whole test session,
# regardless of what a real local .env file holds. pydantic-settings reads
# straight from .env unless an OS env var of the same name already exists -
# an explicit "" wins over .env and is falsy, so the app's mock-selection
# logic (`if settings.x_api_key:`) always picks mocks in tests. Without this,
# adding real keys to .env for local dev/deploy silently breaks tests that
# assume a pristine, empty environment (confirmed: both provider-selection
# tests and webhook signature-verification tests failed this way once real
# WhatsApp/Gemini/etc. credentials were added to .env).
for _credential_var in [
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_FACT_CHECK_API_KEY",
    "GOOGLE_CLOUD_VISION_API_KEY",
    "GOOGLE_TRANSLATE_API_KEY",
    "SIGHTENGINE_API_USER",
    "SIGHTENGINE_API_SECRET",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
]:
    os.environ[_credential_var] = ""


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
