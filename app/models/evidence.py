import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base
from app.models.enums import EvidenceType, Stance
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.source import Source
    from app.models.verification import Verification


class Evidence(Base, UUIDPKMixin, TimestampMixin):
    """One piece of evidence (a fact-check result, web search hit, image
    match, or OCR extraction) gathered and ranked in support of a
    verification's verdict."""

    __tablename__ = "evidence"

    verification_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("verifications.id"), nullable=False, index=True
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("sources.id"), nullable=True)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        SAEnum(EvidenceType, native_enum=False, length=16), nullable=False
    )
    claim_snippet: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stance: Mapped[Stance] = mapped_column(SAEnum(Stance, native_enum=False, length=16), default=Stance.neutral)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    verification: Mapped["Verification"] = relationship(back_populates="evidence_items")
    source: Mapped[Optional["Source"]] = relationship(back_populates="evidence_items")
