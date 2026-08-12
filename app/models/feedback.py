import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base
from app.models.enums import FeedbackRating
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.verification import Verification

COMMENT_MAX_LEN = 500


class Feedback(Base, UUIDPKMixin, TimestampMixin):
    """User-submitted feedback on a verification's usefulness/correctness."""

    __tablename__ = "feedback"

    verification_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("verifications.id"), nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    rating: Mapped[FeedbackRating] = mapped_column(SAEnum(FeedbackRating, native_enum=False, length=16), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(COMMENT_MAX_LEN), nullable=True)

    verification: Mapped["Verification"] = relationship(back_populates="feedback_items")
