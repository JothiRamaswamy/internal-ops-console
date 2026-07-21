import pytest

from app.errors import AppError
from app.models.audit import AuditEvent
from app.models.enums import PaymentStatus, RefundReason, RefundStatus
from app.services import refund_service
from tests.conftest import make_payment


def _create(db, payment, user, amount, key="k-00000001", reason=RefundReason.OTHER):
    return refund_service.create_refund(
        db, payment_id=payment.id, user=user, amount_minor=amount,
        reason=reason, idempotency_key=key,
    )


def test_full_refund_succeeds(db, users, customer):
    p = make_payment(db, customer, amount_minor=10000)
    r = _create(db, p, users["ADMIN"], 10000)
    assert r.status == RefundStatus.SUCCEEDED
    db.refresh(p)
    assert p.status == PaymentStatus.FULLY_REFUNDED


def test_partial_refund_succeeds(db, users, customer):
    p = make_payment(db, customer, amount_minor=10000)
    r = _create(db, p, users["ADMIN"], 4000)
    assert r.status == RefundStatus.SUCCEEDED
    db.refresh(p)
    assert p.status == PaymentStatus.PARTIALLY_REFUNDED
    assert refund_service.remaining_refundable_minor(p) == 6000


def test_refund_over_remaining_fails(db, users, customer):
    p = make_payment(db, customer, amount_minor=5000)
    with pytest.raises(AppError) as exc:
        _create(db, p, users["ADMIN"], 6000)
    assert exc.value.code == "REFUND_AMOUNT_EXCEEDED"


def test_refund_over_role_limit_fails(db, users, customer):
    p = make_payment(db, customer, amount_minor=100000)
    with pytest.raises(AppError) as exc:
        _create(db, p, users["SUPPORT_AGENT"], 50000)  # over $250 limit
    assert exc.value.code == "REFUND_LIMIT_EXCEEDED"


def test_failed_payment_cannot_be_refunded(db, users, customer):
    p = make_payment(db, customer, status=PaymentStatus.FAILED)
    with pytest.raises(AppError) as exc:
        _create(db, p, users["ADMIN"], 100)
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_duplicate_idempotency_key_returns_original(db, users, customer):
    p = make_payment(db, customer, amount_minor=10000)
    r1 = _create(db, p, users["ADMIN"], 1000, key="dupe-key-001")
    r2 = _create(db, p, users["ADMIN"], 9999, key="dupe-key-001")
    assert r1.id == r2.id
    assert r2.amount_minor == 1000


def test_provider_failure_produces_failed_refund(db, users, customer):
    p = make_payment(db, customer, amount_minor=10000,
                     provider_pid="pi_mock_9999_FAIL")
    r = _create(db, p, users["ADMIN"], 1000)
    assert r.status == RefundStatus.FAILED
    assert r.failure_reason
    db.refresh(p)
    # A failed refund must not change the payment status.
    assert p.status == PaymentStatus.SUCCEEDED


def test_payment_status_updates_and_audit(db, users, customer):
    p = make_payment(db, customer, amount_minor=10000)
    r = _create(db, p, users["ADMIN"], 10000)
    events = db.query(AuditEvent).filter_by(entity_id=r.id).all()
    actions = {e.action for e in events}
    assert "REFUND_REQUESTED" in actions
    assert "REFUND_SUCCEEDED" in actions


def test_zero_amount_rejected(db, users, customer):
    p = make_payment(db, customer)
    with pytest.raises(AppError) as exc:
        _create(db, p, users["ADMIN"], 0)
    assert exc.value.code == "VALIDATION_ERROR"
