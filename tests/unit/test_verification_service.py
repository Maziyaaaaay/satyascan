import pytest
from sqlalchemy import select

from app.models.enums import Channel, VerificationStatus
from app.models.evidence import Evidence
from app.models.message import Message
from app.models.user import User
from app.providers.bundle import build_mock_providers
from app.services import rate_limit_service, verification_service
from app.services.rate_limit_service import RateLimitExceeded


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    rate_limit_service.reset_rate_limiter_for_tests()
    yield
    rate_limit_service.reset_rate_limiter_for_tests()


@pytest.fixture
def providers():
    return build_mock_providers()


@pytest.mark.asyncio
async def test_process_incoming_produces_completed_verification(db_session, providers):
    verification = await verification_service.process_incoming(
        db_session,
        providers,
        channel=Channel.simulator,
        external_user_id="sim:session-1",
        text="Drinking hot water cures COVID",
    )

    assert verification.status == VerificationStatus.completed
    assert verification.verdict is not None
    assert verification.explanation_text
    assert verification.processing_time_ms is not None


@pytest.mark.asyncio
async def test_process_incoming_persists_evidence_and_sources(db_session, providers):
    verification = await verification_service.process_incoming(
        db_session,
        providers,
        channel=Channel.simulator,
        external_user_id="sim:session-2",
        text="Vaccines cause the disease they prevent",
    )

    result = await db_session.execute(select(Evidence).where(Evidence.verification_id == verification.id))
    evidence_rows = result.scalars().all()
    assert len(evidence_rows) >= 1


@pytest.mark.asyncio
async def test_process_incoming_reuses_existing_user(db_session, providers):
    v1 = await verification_service.process_incoming(
        db_session, providers, channel=Channel.whatsapp, external_user_id="+911234567890", text="claim one"
    )
    v2 = await verification_service.process_incoming(
        db_session, providers, channel=Channel.whatsapp, external_user_id="+911234567890", text="claim two"
    )
    assert v1.user_id == v2.user_id

    result = await db_session.execute(select(User).where(User.id == v1.user_id))
    users = result.scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_message_excerpt_not_stored_without_consent(db_session, providers):
    verification = await verification_service.process_incoming(
        db_session, providers, channel=Channel.simulator, external_user_id="sim:session-3", text="some claim text"
    )

    result = await db_session.execute(select(Message).where(Message.verification_id == verification.id))
    message = result.scalar_one()
    assert message.content_excerpt is None
    assert message.content_hash


@pytest.mark.asyncio
async def test_image_only_message_records_image_metadata(db_session, providers):
    from app.models.image import Image

    verification = await verification_service.process_incoming(
        db_session,
        providers,
        channel=Channel.simulator,
        external_user_id="sim:session-4",
        image_bytes=b"fake-image-bytes",
    )

    assert verification.has_image is True
    result = await db_session.execute(select(Image).where(Image.verification_id == verification.id))
    image = result.scalar_one()
    assert image.image_hash
    assert image.deleted_at is not None
    assert image.temp_path is None


@pytest.mark.asyncio
async def test_rate_limit_exceeded_raises(db_session, providers):
    from app.config import get_settings

    get_settings.cache_clear()
    import os

    os.environ["RATE_LIMIT_PER_MINUTE"] = "1"
    get_settings.cache_clear()
    rate_limit_service.reset_rate_limiter_for_tests()

    try:
        await verification_service.process_incoming(
            db_session, providers, channel=Channel.simulator, external_user_id="sim:rl-user", text="claim one"
        )
        with pytest.raises(RateLimitExceeded):
            await verification_service.process_incoming(
                db_session, providers, channel=Channel.simulator, external_user_id="sim:rl-user", text="claim two"
            )
    finally:
        del os.environ["RATE_LIMIT_PER_MINUTE"]
        get_settings.cache_clear()
        rate_limit_service.reset_rate_limiter_for_tests()
