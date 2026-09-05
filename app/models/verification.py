import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base
from app.models.enums import ConfidenceLabel, IntentType, Language, SourceMediaType, Verdict, VerificationStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.api_log import APILog
    from app.models.evidence import Evidence
    from app.models.feedback import Feedback
    from app.models.image import Image
    from app.models.message import Message
    from app.models.user import User


class Verification(Base, UUIDPKMixin, TimestampMixin):
    """The central record of one fact-check request/response cycle. This is
    what gets retained long-term - the extracted claim and the outcome - not
    the raw forwarded message content (see Message)."""

    __tablename__ = "verifications"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    claim_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    claim_text_hash: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)

    intent_type: Mapped[Optional[IntentType]] = mapped_column(
        SAEnum(IntentType, native_enum=False, length=32), nullable=True
    )
    verdict: Mapped[Optional[Verdict]] = mapped_column(SAEnum(Verdict, native_enum=False, length=16), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[Optional[ConfidenceLabel]] = mapped_column(
        SAEnum(ConfidenceLabel, native_enum=False, length=16), nullable=True
    )
    explanation_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    explanation_language: Mapped[Optional[Language]] = mapped_column(
        SAEnum(Language, native_enum=False, length=8), nullable=True
    )
    rationale: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, native_enum=False, length=16),
        default=VerificationStatus.pending,
        nullable=False,
    )
    has_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_media_type: Mapped[SourceMediaType] = mapped_column(
        SAEnum(SourceMediaType, native_enum=False, length=16),
        default=SourceMediaType.text,
        nullable=False,
    )
    # Whether any evidence backing this verdict came from a live web search
    # (app.providers.web_search) rather than only the reasoning LLM's own
    # (frozen-at-training-time) knowledge or older fact-check articles. Used
    # to show a freshness caveat on time-sensitive verdicts - see
    # app.services.report_formatting - after a real case of the bot stating
    # a "who currently holds office X" claim with high confidence based on
    # the LLM's own memory, which can go stale.
    is_live_search_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="verifications")
    messages: Mapped[List["Message"]] = relationship(back_populates="verification", cascade="all, delete-orphan")
    images: Mapped[List["Image"]] = relationship(back_populates="verification", cascade="all, delete-orphan")
    evidence_items: Mapped[List["Evidence"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[List["Feedback"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan"
    )
    api_logs: Mapped[List["APILog"]] = relationship(back_populates="verification", cascade="all, delete-orphan")
