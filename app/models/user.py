from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Channel, Language
from app.models.mixins import TimestampMixin, UUIDPKMixin, utcnow

if TYPE_CHECKING:
    from app.models.verification import Verification


class User(Base, UUIDPKMixin, TimestampMixin):
    """A person identified by an encrypted external identifier (WhatsApp phone
    number, or a simulator session id for local testing). Raw identifiers are
    never stored in plaintext - only a Fernet-encrypted value (for replying)
    plus a one-way hash (for lookup), per the privacy-first design."""

    __tablename__ = "users"

    phone_number_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    phone_number_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel, native_enum=False, length=32), nullable=False)
    preferred_language: Mapped[Language] = mapped_column(
        SAEnum(Language, native_enum=False, length=8), default=Language.en, nullable=False
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    verifications: Mapped[List["Verification"]] = relationship(back_populates="user")
