"""Sync / ETL layer: integration source tables -> normalized domain tables.

This is the *inbound* half of the integration story. The `integration_*` tables
are read-only mirrors of what each vendor exposes (populated by a batch pull; in
the prototype, by the seed). This module reads those raw rows and normalizes them
into the console's domain model:

    integration_persona_inquiries  ->  kyc_cases (+ kyc_case_events)
    integration_stripe_charges     ->  payments

The transform is idempotent: rows are upserted by their natural key
(`vendor_reference_id` for KYC, `provider_payment_id` for payments), so a sync
can be re-run for backfills or reconciliation without creating duplicates. It
never overrides operator-owned state (a reviewer's KYC decision, an in-console
refund) — the human decision always wins over a later vendor snapshot.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.customer import Customer
from app.models.enums import KycStatus, KycVendor, PaymentProvider, PaymentStatus
from app.models.integrations import (
    IntegrationPersonaInquiry,
    IntegrationStripeCharge,
)
from app.models.kyc import KycCase, KycCaseEvent
from app.models.payment import Payment
from app.providers.kyc import map_persona_status, risk_level_from_score
from app.providers.payment import map_stripe_status

# A reviewer's decision (or an in-progress review) is owned by the console, so a
# later vendor snapshot must not silently reopen or overwrite it.
KYC_OPERATOR_OWNED = {
    KycStatus.REQUESTED_MORE_INFO,
    KycStatus.APPROVED,
    KycStatus.REJECTED,
}
# Once refunds have been issued in-console the payment status is derived from
# them, not from the vendor snapshot.
PAYMENT_OPERATOR_OWNED = {
    PaymentStatus.PARTIALLY_REFUNDED,
    PaymentStatus.FULLY_REFUNDED,
}


def _resolve_customer(
    db: Session,
    *,
    email: str | None,
    first: str | None,
    last: str | None,
    country: str | None,
) -> Customer:
    """Entity resolution: attach vendor data to *our* customer, matched by email.

    Falls back to creating a minimal customer when the email is unknown so the
    domain row always has a valid owner (real systems would queue these for
    manual matching).
    """
    if email:
        existing = db.scalar(select(Customer).where(Customer.email == email))
        if existing is not None:
            return existing
    resolved_email = email or f"unknown+{utcnow().timestamp()}@example.com"
    local = resolved_email.split("@")[0]
    customer = Customer(
        email=resolved_email,
        first_name=first or local.split(".")[0].title() or "Unknown",
        last_name=last or "Unknown",
        country_code=(country or "US")[:2],
    )
    db.add(customer)
    db.flush()
    return customer


def sync_persona_inquiries(db: Session) -> dict[str, int]:
    """Normalize Persona inquiries into KYC cases + append case events."""
    created = updated = skipped = 0
    inquiries = db.scalars(select(IntegrationPersonaInquiry)).all()
    for inq in inquiries:
        target = map_persona_status(inq.status)
        case = db.scalar(
            select(KycCase).where(
                KycCase.vendor_reference_id == inq.reference_id
            )
        )
        if case is None:
            customer = _resolve_customer(
                db,
                email=inq.email_address,
                first=inq.name_first,
                last=inq.name_last,
                country=inq.country_code,
            )
            submitted = inq.created_at_source or utcnow()
            case = KycCase(
                customer_id=customer.id,
                vendor=KycVendor.PERSONA,
                vendor_reference_id=inq.reference_id,
                status=target,
                risk_level=risk_level_from_score(inq.risk_score),
                risk_score=inq.risk_score,
                country_code=(inq.country_code or customer.country_code)[:2],
                submitted_at=submitted,
                raw_vendor_payload=inq.raw,
            )
            db.add(case)
            db.flush()
            db.add(KycCaseEvent(
                kyc_case_id=case.id, event_type="KYC_CASE_CREATED",
                from_status=None, to_status=KycStatus.PENDING_VENDOR,
                event_metadata={"source": "persona_sync"}, created_at=submitted,
            ))
            if target != KycStatus.PENDING_VENDOR:
                db.add(KycCaseEvent(
                    kyc_case_id=case.id, event_type="KYC_VENDOR_COMPLETED",
                    from_status=KycStatus.PENDING_VENDOR, to_status=target,
                    event_metadata={"source": "persona_sync"},
                    created_at=submitted + timedelta(minutes=30),
                ))
            created += 1
            continue

        # Existing case: never touch operator-owned state; only advance when the
        # normalized vendor status actually changed.
        if case.status in KYC_OPERATOR_OWNED or target == case.status:
            skipped += 1
            continue
        from_status = case.status
        case.status = target
        case.risk_score = inq.risk_score
        case.risk_level = risk_level_from_score(inq.risk_score)
        case.raw_vendor_payload = inq.raw
        db.add(KycCaseEvent(
            kyc_case_id=case.id, event_type="KYC_VENDOR_SYNCED",
            from_status=from_status, to_status=target,
            event_metadata={"source": "persona_sync"},
        ))
        updated += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def sync_stripe_charges(db: Session) -> dict[str, int]:
    """Normalize Stripe charges into payments."""
    created = updated = skipped = 0
    charges = db.scalars(select(IntegrationStripeCharge)).all()
    for ch in charges:
        provider_payment_id = ch.payment_intent or ch.charge_id
        target = map_stripe_status(ch.status, ch.amount, ch.amount_refunded)
        payment = db.scalar(
            select(Payment).where(
                Payment.provider_payment_id == provider_payment_id
            )
        )
        if payment is None:
            customer = _resolve_customer(
                db, email=ch.customer_email, first=None, last=None,
                country=None,
            )
            order_id = str(
                (ch.raw or {}).get("metadata", {}).get("order_id")
                or f"ORD-{ch.charge_id}"
            )
            payment = Payment(
                provider=PaymentProvider.STRIPE,
                provider_payment_id=provider_payment_id,
                customer_id=customer.id,
                order_id=order_id,
                amount_minor=ch.amount,
                currency=ch.currency.upper(),
                status=target,
                payment_method_brand=ch.card_brand,
                payment_method_last4=ch.card_last4,
                created_at=ch.created_at_source or utcnow(),
            )
            db.add(payment)
            created += 1
            continue

        # Don't clobber a status the console derives from in-app refunds.
        if payment.status in PAYMENT_OPERATOR_OWNED or target == payment.status:
            skipped += 1
            continue
        payment.status = target
        updated += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def sync_all(db: Session) -> dict[str, dict[str, int]]:
    """Run the full inbound sync and return per-source counts."""
    return {
        "persona_kyc": sync_persona_inquiries(db),
        "stripe_payments": sync_stripe_charges(db),
    }
