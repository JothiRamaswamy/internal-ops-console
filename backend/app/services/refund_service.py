from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.enums import PaymentStatus, RefundReason, RefundStatus
from app.models.payment import Payment, Refund
from app.models.user import User
from app.permissions import refund_limit_for, require_permission
from app.providers.payment import RefundInput, get_payment_provider
from app.services.audit_service import record_audit

REFUNDABLE_PAYMENT_STATUSES = {
    PaymentStatus.SUCCEEDED,
    PaymentStatus.PARTIALLY_REFUNDED,
}


def refunded_minor(payment: Payment) -> int:
    """Sum of successful refunds. Never trust client-provided totals."""
    return sum(
        r.amount_minor for r in payment.refunds if r.status == RefundStatus.SUCCEEDED
    )


def remaining_refundable_minor(payment: Payment) -> int:
    return max(payment.amount_minor - refunded_minor(payment), 0)


def _refunded_minor_db(db: Session, payment_id: str) -> int:
    """Authoritative refunded total read from the database (post-flush)."""
    total = db.scalar(
        select(func.coalesce(func.sum(Refund.amount_minor), 0))
        .where(Refund.payment_id == payment_id)
        .where(Refund.status == RefundStatus.SUCCEEDED)
    )
    return int(total or 0)


def _recalculate_payment_status(db: Session, payment: Payment) -> None:
    if payment.status in {PaymentStatus.FAILED, PaymentStatus.DISPUTED}:
        return
    refunded = _refunded_minor_db(db, payment.id)
    if refunded <= 0:
        payment.status = PaymentStatus.SUCCEEDED
    elif refunded >= payment.amount_minor:
        payment.status = PaymentStatus.FULLY_REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED


def create_refund(
    db: Session,
    *,
    payment_id: str,
    user: User,
    amount_minor: int,
    reason: RefundReason,
    idempotency_key: str,
    note: str | None = None,
    ip: str | None = None,
) -> Refund:
    require_permission(user, "refund:create")

    # Idempotency: an existing key returns the original result unchanged.
    existing = db.scalar(
        select(Refund).where(Refund.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    if amount_minor <= 0:
        raise AppError("VALIDATION_ERROR", "Refund amount must be greater than zero.")

    # Lock the payment row so concurrent refunds can't exceed the balance.
    payment = db.get(Payment, payment_id, with_for_update=True)
    if payment is None:
        raise AppError("NOT_FOUND", f"Payment {payment_id} was not found.")

    if payment.status == PaymentStatus.FAILED:
        raise AppError(
            "INVALID_STATE_TRANSITION", "Failed payments cannot be refunded."
        )
    if payment.status == PaymentStatus.FULLY_REFUNDED:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            "This payment has already been fully refunded.",
        )
    if payment.status not in REFUNDABLE_PAYMENT_STATUSES:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            f"Payments with status {payment.status.value} cannot be refunded.",
            {"status": payment.status.value},
        )

    remaining = remaining_refundable_minor(payment)
    if amount_minor > remaining:
        raise AppError(
            "REFUND_AMOUNT_EXCEEDED",
            "The refund exceeds the remaining refundable amount.",
            {"remaining_refundable_minor": remaining, "requested_minor": amount_minor},
        )

    limit = refund_limit_for(user)
    if limit is not None and amount_minor > limit:
        raise AppError(
            "REFUND_LIMIT_EXCEEDED",
            "This refund exceeds your role's refund limit.",
            {"limit_minor": limit, "requested_minor": amount_minor},
        )

    refund = Refund(
        payment_id=payment.id,
        amount_minor=amount_minor,
        currency=payment.currency,
        reason=reason,
        note=note,
        status=RefundStatus.PENDING,
        requested_by_id=user.id,
        idempotency_key=idempotency_key,
    )
    db.add(refund)
    db.flush()

    record_audit(
        db,
        actor_id=user.id,
        action="REFUND_REQUESTED",
        entity_type="Refund",
        entity_id=refund.id,
        after={"amount_minor": amount_minor, "payment_id": payment.id,
               "reason": reason.value},
        ip_address=ip,
    )

    provider = get_payment_provider(payment.provider.value)
    result = provider.create_refund(
        RefundInput(
            provider_payment_id=payment.provider_payment_id,
            amount_minor=amount_minor,
            currency=payment.currency,
            idempotency_key=idempotency_key,
        )
    )

    if result.success:
        refund.status = RefundStatus.SUCCEEDED
        refund.provider_refund_id = result.provider_refund_id
        db.flush()
        _recalculate_payment_status(db, payment)
        remaining = remaining_refundable_minor(payment)
        if payment.status == PaymentStatus.FULLY_REFUNDED:
            refund.status_note = "Full refund processed; payment fully refunded."
        else:
            refund.status_note = (
                f"Partial refund processed; ${remaining / 100:,.2f} still refundable."
            )
        record_audit(
            db,
            actor_id=user.id,
            action="REFUND_SUCCEEDED",
            entity_type="Refund",
            entity_id=refund.id,
            after={"status": refund.status.value,
                   "provider_refund_id": refund.provider_refund_id,
                   "payment_status": payment.status.value},
            ip_address=ip,
        )
    else:
        refund.status = RefundStatus.FAILED
        refund.failure_reason = result.failure_reason
        refund.status_note = "Refund failed at the provider; no funds were moved."
        record_audit(
            db,
            actor_id=user.id,
            action="REFUND_FAILED",
            entity_type="Refund",
            entity_id=refund.id,
            after={"status": refund.status.value,
                   "failure_reason": refund.failure_reason},
            ip_address=ip,
        )

    db.commit()
    db.refresh(refund)
    return refund
