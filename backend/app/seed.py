"""Deterministic seed data for the Internal Operations Console.

Run with:  python -m app.seed
A fixed RNG seed keeps screenshots and tests stable.

The seed models the real data flow: it populates the `integration_*` source
tables (the raw vendor mirrors), then runs the sync/ETL layer to normalize them
into the domain tables (`kyc_cases` + events, `payments`). Operator-owned data —
KYC review decisions and in-console refunds — is layered on *after* the sync,
because it originates inside the console rather than from a vendor. Feature flags
are console-owned and have no integration source.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.models import (
    AuditEvent,
    Base,
    Customer,
    FeatureFlag,
    FeatureFlagValue,
    FeatureFlagVersion,
    IntegrationPersonaInquiry,
    IntegrationStripeCharge,
    KycCase,
    KycCaseEvent,
    Payment,
    Refund,
    User,
)
from app.models.enums import (
    FeatureFlagEnvironment,
    FeatureFlagType,
    KycStatus,
    PaymentStatus,
    RefundReason,
    RefundStatus,
    RiskLevel,
    UserRole,
)
from app.services import sync_service

RNG = random.Random(42)
NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)

FIRST_NAMES = [
    "Ava", "Liam", "Mia", "Noah", "Emma", "Oliver", "Sophia", "Lucas", "Isabella",
    "Ethan", "Amelia", "Mason", "Harper", "Elijah", "Aria", "James", "Layla",
    "Ben", "Chloe", "Henry", "Zoe", "Leo", "Nora", "Adam", "Ruby", "Yusuf",
    "Priya", "Wei", "Sofia", "Omar",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Nguyen", "Kim", "Patel", "Chen", "Khan", "Silva", "Haddad", "Novak", "Ali",
    "Rossi",
]
COUNTRIES = ["US", "GB", "CA", "DE", "FR", "AU", "IN", "BR", "NG", "SG"]
CARD_BRANDS = ["visa", "mastercard", "amex", "discover"]


def _dt(days_ago: float) -> datetime:
    return NOW - timedelta(days=days_ago)


def clear(db: Session) -> None:
    for model in (
        AuditEvent, KycCaseEvent, KycCase, Refund, Payment,
        FeatureFlagVersion, FeatureFlagValue, FeatureFlag,
        IntegrationPersonaInquiry, IntegrationStripeCharge,
        Customer, User,
    ):
        db.execute(delete(model))
    db.commit()


def seed_users(db: Session) -> dict[str, User]:
    specs = [
        ("user_admin", "admin@example.com", "Alex Admin", UserRole.ADMIN),
        ("user_ops", "ops@example.com", "Olivia Ops", UserRole.OPS_REVIEWER),
        ("user_support", "support@example.com", "Sam Support", UserRole.SUPPORT_AGENT),
        ("user_readonly", "readonly@example.com", "Riley Readonly",
         UserRole.READ_ONLY),
    ]
    users: dict[str, User] = {}
    for uid, email, name, role in specs:
        u = User(id=uid, email=email, name=name, role=role)
        db.add(u)
        users[role.value] = u
    db.commit()
    return users


def seed_customers(db: Session) -> list[Customer]:
    customers: list[Customer] = []
    for i in range(28):
        first = RNG.choice(FIRST_NAMES)
        last = RNG.choice(LAST_NAMES)
        c = Customer(
            id=f"cust_{i:03d}",
            email=f"{first.lower()}.{last.lower()}{i}@example.com",
            first_name=first,
            last_name=last,
            date_of_birth=datetime(
                RNG.randint(1960, 2003), RNG.randint(1, 12), RNG.randint(1, 28)
            ).date(),
            country_code=RNG.choice(COUNTRIES),
        )
        db.add(c)
        customers.append(c)
    db.commit()
    return customers


# --- Integration SOURCE tables (raw vendor mirrors) ---------------------------

def seed_persona_source(db: Session, customers) -> None:
    """Seed Persona inquiries — the raw KYC vendor source the sync reads from."""
    # "completed" -> NEEDS_REVIEW, "pending" -> PENDING_VENDOR (vendor still working).
    source_statuses = ["completed"] * 24 + ["pending"] * 8
    RNG.shuffle(source_statuses)

    for i, status in enumerate(source_statuses):
        customer = RNG.choice(customers)
        risk = RNG.choices(
            [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL],
            weights=[40, 35, 18, 7],
        )[0]
        risk_score = {
            RiskLevel.LOW: RNG.randint(0, 30),
            RiskLevel.MEDIUM: RNG.randint(31, 60),
            RiskLevel.HIGH: RNG.randint(61, 85),
            RiskLevel.CRITICAL: RNG.randint(86, 100),
        }[risk]
        submitted = _dt(RNG.uniform(0.2, 40))
        raw = {
            "id": f"inq_{i:04d}",
            "status": status,
            "reference_id": f"persona_ref_{i:04d}",
            "attributes": {
                "checks": {
                    "government_id": "passed" if risk_score < 80 else "failed",
                    "selfie": "passed" if risk_score < 90 else "requires_review",
                    "watchlist": "clear" if risk != RiskLevel.CRITICAL else "hit",
                    "database": "passed",
                },
                "risk_score": risk_score,
            },
        }
        db.add(IntegrationPersonaInquiry(
            inquiry_id=f"inq_{i:04d}",
            reference_id=f"persona_ref_{i:04d}",
            status=status,
            name_first=customer.first_name,
            name_last=customer.last_name,
            email_address=customer.email,
            country_code=customer.country_code,
            risk_score=risk_score,
            created_at_source=submitted,
            raw=raw,
        ))
    db.commit()


def seed_stripe_source(db: Session, customers) -> None:
    """Seed Stripe charges — the raw payments vendor source the sync reads from."""
    for i in range(44):
        customer = RNG.choice(customers)
        amount = RNG.choice([1999, 4999, 9900, 12500, 25000, 45000, 199900, 250000])
        created = _dt(RNG.uniform(0.1, 60))
        currency = "usd"
        status = "succeeded"
        if i in (2, 5):
            status = "disputed"
        elif i in (3, 9):
            status = "failed"
        # One charge whose provider id ends in FAIL: the mock refund provider
        # will decline refunds against it (used to demo failed refunds).
        payment_intent = f"pi_stripe_{i:04d}"
        if i == 7:
            payment_intent = "pi_stripe_0007_FAIL"
        brand = RNG.choice(CARD_BRANDS)
        last4 = f"{RNG.randint(0, 9999):04d}"
        db.add(IntegrationStripeCharge(
            charge_id=f"ch_{i:04d}",
            payment_intent=payment_intent,
            amount=amount,
            amount_refunded=0,
            currency=currency,
            status=status,
            customer_email=customer.email,
            card_brand=brand,
            card_last4=last4,
            created_at_source=created,
            raw={
                "id": f"ch_{i:04d}", "object": "charge", "amount": amount,
                "currency": currency, "status": status,
                "payment_intent": payment_intent,
                "payment_method_details": {"card": {"brand": brand, "last4": last4}},
                "metadata": {"order_id": f"ORD-{10000 + i}"},
            },
        ))
    db.commit()


# --- Operator-owned data (layered on AFTER the sync) --------------------------

def seed_kyc_decisions(db: Session, users) -> None:
    """Simulate historical reviewer decisions on synced NEEDS_REVIEW cases."""
    reviewers = [users["ADMIN"], users["OPS_REVIEWER"]]
    cases = db.scalars(
        select(KycCase)
        .where(KycCase.status == KycStatus.NEEDS_REVIEW)
        .order_by(KycCase.vendor_reference_id)
    ).all()
    # Decide a deterministic subset; the rest stay in the review queue.
    plan = ["approve"] * 8 + ["reject"] * 5 + ["more_info"] * 2
    for case, action in zip(cases, plan):
        reviewer = RNG.choice(reviewers)
        decided_at = case.submitted_at + timedelta(hours=RNG.randint(1, 72))
        case.assigned_reviewer_id = reviewer.id
        if action == "approve":
            case.status = KycStatus.APPROVED
            case.decided_by_id = reviewer.id
            case.decided_at = decided_at
            case.decision_note = "Verified during review."
            db.add(KycCaseEvent(
                kyc_case_id=case.id, actor_id=reviewer.id,
                event_type="KYC_CASE_APPROVED",
                from_status=KycStatus.NEEDS_REVIEW, to_status=KycStatus.APPROVED,
                created_at=decided_at,
            ))
            db.add(AuditEvent(
                actor_id=reviewer.id, action="KYC_CASE_APPROVED",
                entity_type="KycCase", entity_id=case.id,
                after={"status": "APPROVED"}, created_at=decided_at,
            ))
        elif action == "reject":
            reason = RNG.choice(
                ["IDENTITY_MISMATCH", "SUSPECTED_FRAUD", "WATCHLIST_MATCH",
                 "DOCUMENT_UNVERIFIABLE"]
            )
            case.status = KycStatus.REJECTED
            case.decided_by_id = reviewer.id
            case.decided_at = decided_at
            case.decision_reason = reason
            case.decision_note = "Rejected during review."
            db.add(KycCaseEvent(
                kyc_case_id=case.id, actor_id=reviewer.id,
                event_type="KYC_CASE_REJECTED",
                from_status=KycStatus.NEEDS_REVIEW, to_status=KycStatus.REJECTED,
                event_metadata={"reason": reason}, created_at=decided_at,
            ))
            db.add(AuditEvent(
                actor_id=reviewer.id, action="KYC_CASE_REJECTED",
                entity_type="KycCase", entity_id=case.id,
                after={"status": "REJECTED", "reason": reason},
                created_at=decided_at,
            ))
        else:  # more_info
            case.status = KycStatus.REQUESTED_MORE_INFO
            db.add(KycCaseEvent(
                kyc_case_id=case.id, actor_id=reviewer.id,
                event_type="KYC_MORE_INFO_REQUESTED",
                from_status=KycStatus.NEEDS_REVIEW,
                to_status=KycStatus.REQUESTED_MORE_INFO,
                created_at=decided_at,
            ))
    db.commit()


def _refund_at(payment_created: datetime) -> datetime:
    """A refund time shortly after the payment, never in the future."""
    latest = min(NOW, payment_created + timedelta(days=3))
    if latest <= payment_created:
        return payment_created + timedelta(hours=2)
    span = (latest - payment_created).total_seconds()
    return payment_created + timedelta(seconds=RNG.uniform(span * 0.1, span))


def _requester_for(amount_minor: int, users) -> User:
    """Pick a seed requester whose role limit actually covers the amount."""
    if amount_minor <= 25_000:
        return users["SUPPORT_AGENT"]
    if amount_minor <= 200_000:
        return users["OPS_REVIEWER"]
    return users["ADMIN"]


def seed_refunds(db: Session, users) -> None:
    """Create in-console refunds against synced, succeeded payments.

    Refunds are operator-owned: they set the payment status, record an audit
    event, and reconcile the vendor snapshot's ``amount_refunded`` (as the next
    sync would once the provider reports the refund).
    """
    charges = {
        (c.payment_intent or c.charge_id): c
        for c in db.scalars(select(IntegrationStripeCharge)).all()
    }
    payments = db.scalars(
        select(Payment)
        .where(Payment.status == PaymentStatus.SUCCEEDED)
        .order_by(Payment.provider_payment_id)
    ).all()
    for i, p in enumerate(payments):
        charge = charges.get(p.provider_payment_id)
        if p.provider_payment_id.endswith("FAIL"):
            # A refund attempt the provider declined — no balance consumed.
            requester = users["SUPPORT_AGENT"]
            db.add(Refund(
                payment_id=p.id, amount_minor=min(p.amount_minor, 5000),
                currency=p.currency, reason=RefundReason.CUSTOMER_REQUEST,
                status=RefundStatus.FAILED,
                failure_reason="Provider declined the refund (simulated failure).",
                requested_by_id=requester.id,
                idempotency_key=f"seed-refund-{i}-failed",
                created_at=_refund_at(p.created_at),
            ))
            continue
        if i % 5 == 0:
            # Full refund.
            refunded_at = _refund_at(p.created_at)
            requester = _requester_for(p.amount_minor, users)
            db.add(Refund(
                payment_id=p.id, amount_minor=p.amount_minor, currency=p.currency,
                reason=RefundReason.DUPLICATE_CHARGE, status=RefundStatus.SUCCEEDED,
                requested_by_id=requester.id,
                idempotency_key=f"seed-refund-{i}-full",
                provider_refund_id=f"re_seed_{i}f",
                created_at=refunded_at,
            ))
            p.status = PaymentStatus.FULLY_REFUNDED
            if charge is not None:
                charge.amount_refunded = p.amount_minor
            db.add(AuditEvent(
                actor_id=requester.id, action="REFUND_SUCCEEDED",
                entity_type="Refund", entity_id=p.id,
                after={"amount_minor": p.amount_minor, "type": "full"},
                created_at=refunded_at,
            ))
        elif i % 3 == 0:
            # Partial refund.
            r_amt = p.amount_minor // RNG.choice([2, 3, 4])
            refunded_at = _refund_at(p.created_at)
            requester = _requester_for(r_amt, users)
            db.add(Refund(
                payment_id=p.id, amount_minor=r_amt, currency=p.currency,
                reason=RNG.choice(list(RefundReason)), status=RefundStatus.SUCCEEDED,
                requested_by_id=requester.id,
                idempotency_key=f"seed-refund-{i}-a",
                provider_refund_id=f"re_seed_{i}a",
                created_at=refunded_at,
            ))
            p.status = PaymentStatus.PARTIALLY_REFUNDED
            if charge is not None:
                charge.amount_refunded = r_amt
            db.add(AuditEvent(
                actor_id=requester.id, action="REFUND_SUCCEEDED",
                entity_type="Refund", entity_id=p.id,
                after={"amount_minor": r_amt, "type": "partial"},
                created_at=refunded_at,
            ))
    db.commit()


# --- Feature flags (console-owned) --------------------------------------------

FLAG_SPECS = [
    ("checkout-v2", "New checkout experience", "payments", ["checkout", "revenue"]),
    ("kyc-auto-approve", "Auto-approve low risk KYC", "risk", ["kyc", "automation"]),
    ("refund-self-service", "Customer self-service refunds", "support",
     ["refunds"]),
    ("new-dashboard-ui", "Redesigned internal dashboard", "platform", ["ui"]),
    ("fraud-scoring-v3", "Fraud scoring model v3", "risk", ["fraud", "ml"]),
    ("instant-payouts", "Instant payout rails", "payments", ["payouts"]),
    ("beta-invoicing", "Beta invoicing module", "billing", ["billing", "beta"]),
    ("dark-mode", "Dark mode theme", "platform", ["ui"]),
    ("sms-notifications", "SMS notifications", "growth", ["notifications"]),
    ("multi-currency", "Multi-currency support", "payments", ["intl"]),
    ("audit-export", "Audit log CSV export", "compliance", ["audit"]),
    ("rate-limit-api", "Stricter API rate limits", "platform",
     ["api", "reliability"]),
    ("legacy-onboarding", "Legacy onboarding flow", "growth", ["deprecated"]),
]


SAMPLE_FILTERS = [
    [],
    [{"property": "plan", "operator": "equals", "value": "enterprise"}],
    [{"property": "country", "operator": "in", "value": "US,CA,GB"}],
    [{"property": "email", "operator": "contains", "value": "@internal.co"}],
]


def _flag_config(enabled: bool, env: FeatureFlagEnvironment) -> dict:
    """Build a PostHog-style rollout config for the seed."""
    if not enabled:
        return {"enabled": False, "rollout_percentage": 0, "filters": []}
    if env == FeatureFlagEnvironment.PRODUCTION:
        pct = RNG.choice([10, 25, 50, 100])
    elif env == FeatureFlagEnvironment.STAGING:
        pct = RNG.choice([50, 100])
    else:
        pct = 100
    return {
        "enabled": True,
        "rollout_percentage": pct,
        "filters": RNG.choice(SAMPLE_FILTERS),
    }


def seed_flags(db: Session, users) -> None:
    envs = list(FeatureFlagEnvironment)
    for i, (key, desc, owner, tags) in enumerate(FLAG_SPECS):
        archived = key == "legacy-onboarding"
        flag = FeatureFlag(
            id=f"flag_{i:03d}",
            key=key,
            description=desc,
            type=FeatureFlagType.BOOLEAN,
            owner=owner,
            tags=tags,
            archived_at=_dt(5) if archived else None,
            created_at=_dt(RNG.uniform(30, 120)),
        )
        db.add(flag)
        db.flush()
        for env in envs:
            enabled = RNG.random() < (
                0.8 if env == FeatureFlagEnvironment.DEVELOPMENT else
                0.5 if env == FeatureFlagEnvironment.STAGING else 0.35
            )
            config = _flag_config(enabled, env)
            version = 1
            fv = FeatureFlagValue(
                flag_id=flag.id, environment=env, value=config, version=version,
                updated_by_id=users["ADMIN"].id,
            )
            db.add(fv)
            db.add(FeatureFlagVersion(
                flag_id=flag.id, environment=env, previous_value=None,
                new_value=config, version=1, reason="Initial value",
                changed_by_id=users["ADMIN"].id, created_at=flag.created_at,
            ))
            # Add a couple of production change records with history.
            if env == FeatureFlagEnvironment.PRODUCTION and i < 4:
                new_config = _flag_config(not enabled, env)
                fv.value = new_config
                fv.version = 2
                fv.updated_by_id = users["ADMIN"].id
                changed_at = _dt(RNG.uniform(1, 6))
                db.add(FeatureFlagVersion(
                    flag_id=flag.id, environment=env, previous_value=config,
                    new_value=new_config, version=2,
                    reason="Gradual production rollout",
                    changed_by_id=users["ADMIN"].id, created_at=changed_at,
                ))
                db.add(AuditEvent(
                    actor_id=users["ADMIN"].id, action="FEATURE_FLAG_UPDATED",
                    entity_type="FeatureFlag", entity_id=flag.id,
                    before={"environment": "PRODUCTION", "value": config},
                    after={"environment": "PRODUCTION", "value": new_config,
                           "version": 2},
                    metadata={"reason": "Gradual production rollout"},
                    created_at=changed_at,
                ))
    db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        clear(db)
        users = seed_users(db)
        customers = seed_customers(db)
        # 1. Land raw vendor records in the integration source tables.
        seed_persona_source(db, customers)
        seed_stripe_source(db, customers)
        # 2. Run the sync/ETL: integration_* -> normalized domain tables.
        sync_summary = sync_service.sync_all(db)
        # Record the sync so the Integrations health page has a "last synced".
        db.add(AuditEvent(
            actor_id=users["ADMIN"].id, action="INTEGRATION_SYNCED",
            entity_type="Integration", entity_id="all",
            after=sync_summary, created_at=NOW - timedelta(minutes=6),
        ))
        db.commit()
        # 3. Layer on operator-owned data that originates in the console.
        seed_kyc_decisions(db, users)
        seed_refunds(db, users)
        seed_flags(db, users)

        kyc_count = db.scalar(select(func.count()).select_from(KycCase))
        pay_count = db.scalar(select(func.count()).select_from(Payment))
        print("Seed complete:")
        print(f"  sync={sync_summary}")
        print(f"  users={len(users)} customers={len(customers)} "
              f"kyc_cases={kyc_count} payments={pay_count} "
              f"flags={len(FLAG_SPECS)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
