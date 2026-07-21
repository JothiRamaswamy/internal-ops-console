"""Integration source (staging) tables.

These stand in for external systems we would integrate with in production. Instead
of calling the real vendor APIs, we seed representative raw records into these
tables; the sync/ETL layer reads them and normalizes them into the domain tables.
Each row mirrors the shape of a real vendor object. Feature flags are
console-owned and have no integration source.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin


class IntegrationPersonaInquiry(IdMixin, Base):
    """Raw Persona identity-verification inquiry (KYC integration source)."""

    __tablename__ = "integration_persona_inquiries"

    inquiry_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    reference_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    name_first: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_last: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at_source: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)


class IntegrationStripeCharge(IdMixin, Base):
    """Raw Stripe charge object (payments integration source)."""

    __tablename__ = "integration_stripe_charges"

    charge_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    payment_intent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_refunded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card_brand: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at_source: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
