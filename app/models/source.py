from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CredibilityTier
from app.models.mixins import UUIDPKMixin, utcnow

if TYPE_CHECKING:
    from app.models.evidence import Evidence


class Source(Base, UUIDPKMixin):
    """A deduplicated publisher/URL referenced by one or more pieces of
    evidence across verifications - reused rather than re-created every time
    the same source is cited again."""

    __tablename__ = "sources"

    url: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String, index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publisher_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    credibility_tier: Mapped[CredibilityTier] = mapped_column(
        SAEnum(CredibilityTier, native_enum=False, length=16), default=CredibilityTier.unknown, nullable=False
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    evidence_items: Mapped[List["Evidence"]] = relationship(back_populates="source")
