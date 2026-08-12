import uuid
from typing import Optional

from sqlalchemy import JSON, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base
from app.models.enums import AuditEventType
from app.models.mixins import TimestampMixin, UUIDPKMixin


class AuditLog(Base, UUIDPKMixin, TimestampMixin):
    """Append-only record of privacy-relevant events (consent changes, data
    deletion, media deletion) - required by Part 12's audit-log principle.
    Not one of the 8 tables named in the original PRD list, added because the
    PRD's own security requirements (consent, audit logs) need somewhere to
    live."""

    __tablename__ = "audit_logs"

    event_type: Mapped[AuditEventType] = mapped_column(
        SAEnum(AuditEventType, native_enum=False, length=32), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    verification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("verifications.id"), nullable=True
    )
    log_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
