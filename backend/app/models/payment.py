from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.enums import (
    PaymentProvider,
    PaymentStatus,
    RefundReason,
    RefundStatus,
    payment_provider_enum,
    payment_status_enum,
    refund_reason_enum,
    refund_status_enum,
)


class Payment(IdMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    provider: Mapped[PaymentProvider] = mapped_column(
        payment_provider_enum, nullable=False
    )
    provider_payment_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    order_id: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(payment_status_enum, nullable=False)
    payment_method_brand: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_method_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)

    customer = relationship("Customer", back_populates="payments")
    refunds = relationship(
        "Refund",
        back_populates="payment",
        order_by="Refund.created_at",
        cascade="all, delete-orphan",
    )


class Refund(IdMixin, TimestampMixin, Base):
    __tablename__ = "refunds"

    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False)
    provider_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[RefundReason] = mapped_column(refund_reason_enum, nullable=False)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[RefundStatus] = mapped_column(refund_status_enum, nullable=False)
    status_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_by_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    payment = relationship("Payment", back_populates="refunds")
    requested_by = relationship("User", back_populates="requested_refunds")
