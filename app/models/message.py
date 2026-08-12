import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base
from app.models.enums import Channel, MessageDirection
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.verification import Verification

EXCERPT_MAX_LEN = 280


class Message(Base, UUIDPKMixin, TimestampMixin):
    """A single inbound/outbound message tied to a verification. Per the
    'no permanent message storage by default' principle, only a content hash
    is stored unless the user has given consent AND retention is enabled -
    in which case a short truncated excerpt is also kept (see
    services.consent_service / config.message_retention_days)."""

    __tablename__ = "messages"

    verification_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("verifications.id"), nullable=False, index=True
    )
    direction: Mapped[MessageDirection] = mapped_column(
        SAEnum(MessageDirection, native_enum=False, length=16), nullable=False
    )
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel, native_enum=False, length=32), nullable=False)
    external_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content_excerpt: Mapped[Optional[str]] = mapped_column(String(EXCERPT_MAX_LEN), nullable=True)

    verification: Mapped["Verification"] = relationship(back_populates="messages")
