import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.verification import Verification

OCR_EXCERPT_MAX_LEN = 500
AI_REASONING_MAX_LEN = 500
C2PA_GENERATOR_MAX_LEN = 200
C2PA_SOURCE_TYPE_MAX_LEN = 300
C2PA_SUMMARY_MAX_LEN = 500


class Image(Base, UUIDPKMixin, TimestampMixin):
    """Metadata about an image submitted for verification. The image bytes
    themselves are written to a temp path during processing and deleted
    immediately after (see services.media_service) - only a hash and a
    processing summary survive, per the privacy-first design."""

    __tablename__ = "images"

    verification_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("verifications.id"), nullable=False, index=True
    )
    image_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    temp_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ocr_text_excerpt: Mapped[Optional[str]] = mapped_column(String(OCR_EXCERPT_MAX_LEN), nullable=True)
    reverse_search_match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_generated_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_generated_reasoning: Mapped[Optional[str]] = mapped_column(String(AI_REASONING_MAX_LEN), nullable=True)

    # Content Credentials (C2PA) provenance-metadata check - see
    # app.services.c2pa_service. A much stronger signal than the perceptual
    # ai_generated_probability above when present, but most images carry no
    # manifest at all (c2pa_has_manifest=False is the common case).
    c2pa_has_manifest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    c2pa_generator: Mapped[Optional[str]] = mapped_column(String(C2PA_GENERATOR_MAX_LEN), nullable=True)
    c2pa_digital_source_type: Mapped[Optional[str]] = mapped_column(String(C2PA_SOURCE_TYPE_MAX_LEN), nullable=True)
    c2pa_is_ai_indicated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    c2pa_summary: Mapped[Optional[str]] = mapped_column(String(C2PA_SUMMARY_MAX_LEN), nullable=True)

    verification: Mapped["Verification"] = relationship(back_populates="images")
