from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, utcnow


class ProcessedWebhookEvent(IdMixin, Base):
    """Idempotency ledger for inbound webhook events."""

    __tablename__ = "processed_webhook_events"

    source: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
