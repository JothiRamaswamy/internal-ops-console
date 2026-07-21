from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, utcnow
from app.models.enums import (
    KycStatus,
    KycVendor,
    RiskLevel,
    kyc_status_enum,
    kyc_vendor_enum,
    risk_level_enum,
)


class KycCase(IdMixin, TimestampMixin, Base):
    __tablename__ = "kyc_cases"

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    vendor: Mapped[KycVendor] = mapped_column(kyc_vendor_enum, nullable=False)
    vendor_reference_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    status: Mapped[KycStatus] = mapped_column(kyc_status_enum, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(risk_level_enum, nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    assigned_reviewer_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    decision_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    raw_vendor_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    customer = relationship("Customer", back_populates="kyc_cases")
    assigned_reviewer = relationship(
        "User",
        back_populates="assigned_kyc_cases",
        foreign_keys=[assigned_reviewer_id],
    )
    decided_by = relationship(
        "User", back_populates="decided_kyc_cases", foreign_keys=[decided_by_id]
    )
    events = relationship(
        "KycCaseEvent",
        back_populates="kyc_case",
        order_by="KycCaseEvent.created_at",
        cascade="all, delete-orphan",
    )


class KycCaseEvent(IdMixin, Base):
    __tablename__ = "kyc_case_events"

    kyc_case_id: Mapped[str] = mapped_column(
        ForeignKey("kyc_cases.id"), nullable=False
    )
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[KycStatus | None] = mapped_column(
        kyc_status_enum, nullable=True
    )
    to_status: Mapped[KycStatus | None] = mapped_column(kyc_status_enum, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    kyc_case = relationship("KycCase", back_populates="events")
    actor = relationship("User")
