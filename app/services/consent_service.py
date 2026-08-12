from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.enums import AuditEventType
from app.models.mixins import utcnow
from app.models.user import User


async def give_consent(db: AsyncSession, user: User) -> None:
    user.consent_given = True
    user.consent_timestamp = utcnow()
    db.add(AuditLog(event_type=AuditEventType.consent_given, user_id=user.id))
    await db.flush()


async def revoke_consent(db: AsyncSession, user: User) -> None:
    user.consent_given = False
    db.add(AuditLog(event_type=AuditEventType.consent_revoked, user_id=user.id))
    await db.flush()


def should_store_excerpt(user: User) -> bool:
    """Per the 'no permanent message storage by default' principle: a
    truncated excerpt is only ever kept if the user has consented AND
    retention is explicitly enabled. Otherwise only a content hash survives."""
    settings = get_settings()
    return bool(user.consent_given) and settings.message_retention_days > 0
