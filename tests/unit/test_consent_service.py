import os

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType, Channel, Language
from app.models.user import User
from app.services import consent_service


@pytest.fixture
def _user():
    return User(
        phone_number_encrypted="enc",
        phone_number_hash="hash",
        channel=Channel.simulator,
        preferred_language=Language.en,
    )


@pytest.mark.asyncio
async def test_give_consent_sets_flag_and_writes_audit_log(db_session, _user):
    db_session.add(_user)
    await db_session.flush()

    await consent_service.give_consent(db_session, _user)

    assert _user.consent_given is True
    assert _user.consent_timestamp is not None

    result = await db_session.execute(select(AuditLog).where(AuditLog.user_id == _user.id))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].event_type == AuditEventType.consent_given


@pytest.mark.asyncio
async def test_revoke_consent_clears_flag(db_session, _user):
    db_session.add(_user)
    await db_session.flush()
    await consent_service.give_consent(db_session, _user)

    await consent_service.revoke_consent(db_session, _user)

    assert _user.consent_given is False


def test_should_store_excerpt_requires_both_consent_and_retention(_user):
    get_settings.cache_clear()
    os.environ["MESSAGE_RETENTION_DAYS"] = "0"
    get_settings.cache_clear()
    _user.consent_given = True
    assert consent_service.should_store_excerpt(_user) is False

    os.environ["MESSAGE_RETENTION_DAYS"] = "30"
    get_settings.cache_clear()
    assert consent_service.should_store_excerpt(_user) is True

    _user.consent_given = False
    assert consent_service.should_store_excerpt(_user) is False

    del os.environ["MESSAGE_RETENTION_DAYS"]
    get_settings.cache_clear()
