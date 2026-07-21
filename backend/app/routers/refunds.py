from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import client_ip, get_current_user
from app.errors import AppError
from app.models.customer import Customer
from app.models.enums import PaymentStatus, RefundStatus
from app.models.payment import Payment
from app.models.user import User
from app.permissions import refund_limit_for, require_permission
from app.schemas import CreateRefundRequest
from app.serializers import payment_detail, payment_row, refund_row
from app.services import refund_service

router = APIRouter(prefix="/api", tags=["refunds"])


@router.get("/payments")
def list_payments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    q: str | None = None,
    payment_id: str | None = None,
    order_id: str | None = None,
    last4: str | None = None,
    status: PaymentStatus | None = None,
    amount_min_minor: int | None = None,
    amount_max_minor: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    require_permission(user, "refund:read")
    stmt = (
        select(Payment)
        .join(Customer, Payment.customer_id == Customer.id)
        .options(selectinload(Payment.customer), selectinload(Payment.refunds))
    )
    if payment_id:
        stmt = stmt.where(Payment.id.ilike(f"%{payment_id}%"))
    if order_id:
        stmt = stmt.where(Payment.order_id.ilike(f"%{order_id}%"))
    if last4:
        stmt = stmt.where(Payment.payment_method_last4 == last4)
    if status:
        stmt = stmt.where(Payment.status == status)
    if amount_min_minor is not None:
        stmt = stmt.where(Payment.amount_minor >= amount_min_minor)
    if amount_max_minor is not None:
        stmt = stmt.where(Payment.amount_minor <= amount_max_minor)
    if created_from:
        stmt = stmt.where(Payment.created_at >= created_from)
    if created_to:
        stmt = stmt.where(Payment.created_at <= created_to)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Customer.email.ilike(like),
                (Customer.first_name + " " + Customer.last_name).ilike(like),
            )
        )

    rows = db.execute(stmt).scalars().all()
    total = len(rows)
    ordered = sorted(rows, key=lambda p: p.created_at, reverse=True)
    page = ordered[offset : offset + limit]
    return {"total": total, "items": [payment_row(p) for p in page]}


@router.get("/payments/summary")
def payments_summary(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    require_permission(user, "refund:read")
    payments = db.execute(
        select(Payment).options(selectinload(Payment.refunds))
    ).scalars().all()
    gross = sum(p.amount_minor for p in payments)
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    refunded_today = 0
    total_refunded = 0
    failed = 0
    for p in payments:
        for r in p.refunds:
            if r.status == RefundStatus.SUCCEEDED:
                total_refunded += r.amount_minor
                if r.created_at >= today:
                    refunded_today += r.amount_minor
            if r.status == RefundStatus.FAILED:
                failed += 1
    refund_rate = (total_refunded / gross) if gross else 0.0
    return {
        "gross_volume_minor": gross,
        "refunded_today_minor": refunded_today,
        "refund_rate": round(refund_rate, 4),
        "failed_refunds": failed,
    }


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_permission(user, "refund:read")
    payment = db.get(Payment, payment_id)
    if not payment:
        raise AppError("NOT_FOUND", f"Payment {payment_id} was not found.")
    detail = payment_detail(payment)
    detail["refund_limit_minor"] = refund_limit_for(user)
    detail["refund_allowed"] = payment.status in {
        PaymentStatus.SUCCEEDED,
        PaymentStatus.PARTIALLY_REFUNDED,
    } and detail["remaining_refundable_minor"] > 0
    return detail


@router.post("/payments/{payment_id}/refunds")
def create_refund(
    payment_id: str,
    body: CreateRefundRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    refund = refund_service.create_refund(
        db,
        payment_id=payment_id,
        user=user,
        amount_minor=body.amount_minor,
        reason=body.reason,
        idempotency_key=body.idempotency_key,
        note=body.note,
        ip=client_ip(request),
    )
    payment = db.get(Payment, payment_id)
    return {"refund": refund_row(refund), "payment": payment_detail(payment)}
