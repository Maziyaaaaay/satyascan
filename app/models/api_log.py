import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base
from app.models.enums import ProviderName
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.verification import Verification


class APILog(Base, UUIDPKMixin, TimestampMixin):
    """A record of one outbound call to an external provider (real or mock),
    for observability/debugging. request_summary must never contain API keys
    or raw PII - callers are responsible for redacting before logging."""

    __tablename__ = "api_logs"

    verification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("verifications.id"), nullable=True, index=True
    )
    provider: Mapped[ProviderName] = mapped_column(SAEnum(ProviderName, native_enum=False, length=32), nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    request_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    verification: Mapped[Optional["Verification"]] = relationship(back_populates="api_logs")
