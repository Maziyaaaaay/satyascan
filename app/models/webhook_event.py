from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class WebhookEvent(Base, UUIDPKMixin, TimestampMixin):
    """Dedup ledger for inbound webhook message IDs, committed in its own
    short transaction the instant a message is claimed - before the
    (potentially slow) verification pipeline runs. WhatsApp delivers
    webhooks at-least-once and will retry if our response is slow, which
    without this produced duplicate replies to a single user message.
    Deliberately a separate table from `messages`: a Message row requires a
    verification_id that doesn't exist yet at claim time."""

    __tablename__ = "webhook_events"

    external_message_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
