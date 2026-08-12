import pytest
from sqlalchemy import select

from app.models.api_log import APILog
from app.models.enums import Channel
from app.providers.bundle import build_mock_providers
from app.services import rate_limit_service, verification_service


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    rate_limit_service.reset_rate_limiter_for_tests()
    yield
    rate_limit_service.reset_rate_limiter_for_tests()


@pytest.mark.asyncio
async def test_process_incoming_writes_api_logs_marked_as_mock(db_session):
    providers = build_mock_providers()
    verification = await verification_service.process_incoming(
        db_session,
        providers,
        channel=Channel.simulator,
        external_user_id="sim:api-log-session",
        text="Drinking hot water cures COVID",
    )

    result = await db_session.execute(select(APILog).where(APILog.verification_id == verification.id))
    logs = result.scalars().all()

    assert len(logs) >= 1
    assert all(log.is_mock is True for log in logs)
    assert all(log.endpoint for log in logs)
