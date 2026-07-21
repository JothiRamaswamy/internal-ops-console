"""Tests for the sync/ETL layer: integration_* source -> normalized domain."""

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models.customer import Customer
from app.models.enums import KycStatus, PaymentStatus, RiskLevel
from app.models.integrations import (
    IntegrationPersonaInquiry,
    IntegrationStripeCharge,
)
from app.models.kyc import KycCase
from app.models.payment import Payment
from app.providers.kyc import map_persona_status, risk_level_from_score
from app.providers.payment import map_stripe_status
from app.services import sync_service


def _inquiry(db, ref, *, status="completed", risk=70, email="c@example.com"):
    inq = IntegrationPersonaInquiry(
        inquiry_id=f"inq_{ref}", reference_id=ref, status=status,
        name_first="Test", name_last="Customer", email_address=email,
        country_code="US", risk_score=risk,
        created_at_source=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw={"reference_id": ref, "status": status},
    )
    db.add(inq)
    db.commit()
    return inq


def _charge(db, cid, *, status="succeeded", amount=10000, refunded=0,
            email="c@example.com", pi=None):
    ch = IntegrationStripeCharge(
        charge_id=cid, payment_intent=pi or f"pi_{cid}", amount=amount,
        amount_refunded=refunded, currency="usd", status=status,
        customer_email=email, card_brand="visa", card_last4="4242",
        created_at_source=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw={"id": cid, "metadata": {"order_id": "ORD-1"}},
    )
    db.add(ch)
    db.commit()
    return ch


# --- Pure normalization helpers ----------------------------------------------

def test_persona_status_mapping():
    assert map_persona_status("completed") == KycStatus.NEEDS_REVIEW
    assert map_persona_status("pending") == KycStatus.PENDING_VENDOR
    # Vendor "approved" is only an input to human review, not a final decision.
    assert map_persona_status("approved") == KycStatus.NEEDS_REVIEW
    assert map_persona_status(None) == KycStatus.PENDING_VENDOR


def test_risk_level_bucketing():
    assert risk_level_from_score(10) == RiskLevel.LOW
    assert risk_level_from_score(45) == RiskLevel.MEDIUM
    assert risk_level_from_score(70) == RiskLevel.HIGH
    assert risk_level_from_score(95) == RiskLevel.CRITICAL
    assert risk_level_from_score(None) == RiskLevel.LOW


def test_stripe_status_mapping():
    assert map_stripe_status("succeeded", 10000, 0) == PaymentStatus.SUCCEEDED
    assert map_stripe_status("failed", 10000, 0) == PaymentStatus.FAILED
    assert map_stripe_status("disputed", 10000, 0) == PaymentStatus.DISPUTED
    assert map_stripe_status("succeeded", 10000, 4000) == (
        PaymentStatus.PARTIALLY_REFUNDED
    )
    assert map_stripe_status("succeeded", 10000, 10000) == (
        PaymentStatus.FULLY_REFUNDED
    )


# --- KYC sync -----------------------------------------------------------------

def test_persona_creates_case_with_events(db, customer):
    _inquiry(db, "ref-1", status="completed", risk=70)
    result = sync_service.sync_persona_inquiries(db)
    assert result == {"created": 1, "updated": 0, "skipped": 0}

    case = db.scalar(select(KycCase).where(KycCase.vendor_reference_id == "ref-1"))
    assert case.status == KycStatus.NEEDS_REVIEW
    assert case.risk_level == RiskLevel.HIGH
    assert case.customer_id == customer.id  # resolved by email
    types = [e.event_type for e in case.events]
    assert types == ["KYC_CASE_CREATED", "KYC_VENDOR_COMPLETED"]


def test_persona_pending_has_no_completed_event(db, customer):
    _inquiry(db, "ref-2", status="pending")
    sync_service.sync_persona_inquiries(db)
    case = db.scalar(select(KycCase).where(KycCase.vendor_reference_id == "ref-2"))
    assert case.status == KycStatus.PENDING_VENDOR
    assert [e.event_type for e in case.events] == ["KYC_CASE_CREATED"]


def test_persona_sync_is_idempotent(db, customer):
    _inquiry(db, "ref-3")
    sync_service.sync_persona_inquiries(db)
    result = sync_service.sync_persona_inquiries(db)
    assert result == {"created": 0, "updated": 0, "skipped": 1}
    assert db.scalar(select(func.count()).select_from(KycCase)) == 1


def test_persona_advances_pending_to_needs_review(db, customer):
    inq = _inquiry(db, "ref-4", status="pending")
    sync_service.sync_persona_inquiries(db)
    inq.status = "completed"
    db.commit()
    result = sync_service.sync_persona_inquiries(db)
    assert result["updated"] == 1
    case = db.scalar(select(KycCase).where(KycCase.vendor_reference_id == "ref-4"))
    assert case.status == KycStatus.NEEDS_REVIEW
    assert "KYC_VENDOR_SYNCED" in [e.event_type for e in case.events]


def test_sync_never_overrides_operator_decision(db, customer):
    _inquiry(db, "ref-5", status="completed")
    sync_service.sync_persona_inquiries(db)
    case = db.scalar(select(KycCase).where(KycCase.vendor_reference_id == "ref-5"))
    case.status = KycStatus.APPROVED
    db.commit()
    # Vendor still reports "completed"; the reviewer decision must stand.
    result = sync_service.sync_persona_inquiries(db)
    assert result["skipped"] == 1
    db.refresh(case)
    assert case.status == KycStatus.APPROVED


def test_persona_resolves_unknown_email_to_new_customer(db):
    _inquiry(db, "ref-6", email="brand-new@example.com")
    sync_service.sync_persona_inquiries(db)
    assert db.scalar(
        select(Customer).where(Customer.email == "brand-new@example.com")
    ) is not None


# --- Payment sync -------------------------------------------------------------

def test_stripe_creates_payment(db, customer):
    _charge(db, "ch-1", status="succeeded", amount=25000, pi="pi_abc")
    result = sync_service.sync_stripe_charges(db)
    assert result == {"created": 1, "updated": 0, "skipped": 0}
    pay = db.scalar(select(Payment).where(Payment.provider_payment_id == "pi_abc"))
    assert pay.status == PaymentStatus.SUCCEEDED
    assert pay.currency == "USD"
    assert pay.amount_minor == 25000
    assert pay.customer_id == customer.id


def test_stripe_maps_failed_and_disputed(db, customer):
    _charge(db, "ch-2", status="failed", pi="pi_f")
    _charge(db, "ch-3", status="disputed", pi="pi_d")
    sync_service.sync_stripe_charges(db)
    failed = db.scalar(select(Payment).where(Payment.provider_payment_id == "pi_f"))
    disputed = db.scalar(select(Payment).where(Payment.provider_payment_id == "pi_d"))
    assert failed.status == PaymentStatus.FAILED
    assert disputed.status == PaymentStatus.DISPUTED


def test_stripe_does_not_clobber_refunded_status(db, customer):
    _charge(db, "ch-4", status="succeeded", pi="pi_r")
    sync_service.sync_stripe_charges(db)
    pay = db.scalar(select(Payment).where(Payment.provider_payment_id == "pi_r"))
    pay.status = PaymentStatus.PARTIALLY_REFUNDED
    db.commit()
    result = sync_service.sync_stripe_charges(db)
    assert result["skipped"] == 1
    db.refresh(pay)
    assert pay.status == PaymentStatus.PARTIALLY_REFUNDED
