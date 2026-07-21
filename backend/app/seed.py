"""Deterministic seed data for the Internal Operations Console.

Run with:  python -m app.seed
A fixed RNG seed keeps screenshots and tests stable.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine
from app.models import (
    AuditEvent,
    Base,
    Customer,
    FeatureFlag,
    FeatureFlagValue,
    FeatureFlagVersion,
    IntegrationLaunchDarklyFlag,
    IntegrationPersonaInquiry,
    IntegrationStripeCharge,
    KycCase,
    KycCaseEvent,
    Payment,
    ProcessedWebhookEvent,
    Refund,
    User,
)
from app.models.enums import (
    FeatureFlagEnvironment,
    FeatureFlagType,
    KycStatus,
    KycVendor,
    PaymentProvider,
    PaymentStatus,
    RefundReason,
    RefundStatus,
    RiskLevel,
    UserRole,
)

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
        FeatureFlagVersion, FeatureFlagValue, FeatureFlag, ProcessedWebhookEvent,
        IntegrationPersonaInquiry, IntegrationStripeCharge,
        IntegrationLaunchDarklyFlag, Customer, User,
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


def seed_kyc(db: Session, customers, users) -> list[KycCase]:
    vendors = [KycVendor.PERSONA, KycVendor.STRIPE_IDENTITY, KycVendor.MOCK_VENDOR]
    reviewers = [users["ADMIN"], users["OPS_REVIEWER"]]

    # Distribution: ensure at least 8 needs_review, 4 high/critical.
    statuses = (
        [KycStatus.NEEDS_REVIEW] * 10
        + [KycStatus.PENDING_VENDOR] * 4
        + [KycStatus.REQUESTED_MORE_INFO] * 3
        + [KycStatus.APPROVED] * 8
        + [KycStatus.REJECTED] * 7
    )
    RNG.shuffle(statuses)

    cases: list[KycCase] = []
    for i, status in enumerate(statuses):
        customer = RNG.choice(customers)
        risk = RNG.choices(
            [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL],
            weights=[40, 35, 18, 7],
        )[0]
        vendor = RNG.choice(vendors)
        submitted = _dt(RNG.uniform(0.2, 40))
        assigned = None
        if status in (KycStatus.NEEDS_REVIEW, KycStatus.REQUESTED_MORE_INFO):
            assigned = RNG.choice([None, *reviewers])
        risk_score = {
            RiskLevel.LOW: RNG.randint(0, 30),
            RiskLevel.MEDIUM: RNG.randint(31, 60),
            RiskLevel.HIGH: RNG.randint(61, 85),
            RiskLevel.CRITICAL: RNG.randint(86, 100),
        }[risk]
        case = KycCase(
            id=f"kyc_{i:03d}",
            customer_id=customer.id,
            vendor=vendor,
            vendor_reference_id=f"{vendor.value.lower()}_ref_{i:04d}",
            status=status,
            risk_level=risk,
            risk_score=risk_score,
            country_code=customer.country_code,
            submitted_at=submitted,
            assigned_reviewer_id=assigned.id if assigned else None,
            raw_vendor_payload={
                "vendor": vendor.value,
                "reference_id": f"{vendor.value.lower()}_ref_{i:04d}",
                "checks": {
                    "document": "passed" if risk_score < 80 else "failed",
                    "selfie": "passed" if risk_score < 90 else "review",
                    "watchlist": "clear" if risk != RiskLevel.CRITICAL else "hit",
                    "address": "passed",
                },
                "risk_score": risk_score,
            },
        )
        if status in (KycStatus.APPROVED, KycStatus.REJECTED):
            reviewer = RNG.choice(reviewers)
            case.decided_by_id = reviewer.id
            case.assigned_reviewer_id = reviewer.id
            case.decided_at = submitted + timedelta(hours=RNG.randint(1, 72))
            if status == KycStatus.REJECTED:
                case.decision_reason = RNG.choice(
                    ["IDENTITY_MISMATCH", "SUSPECTED_FRAUD", "WATCHLIST_MATCH",
                     "DOCUMENT_UNVERIFIABLE"]
                )
                case.decision_note = "Automated seed rejection."
            else:
                case.decision_note = "Verified during seed."
        db.add(case)
        db.flush()

        # Event history.
        db.add(KycCaseEvent(
            kyc_case_id=case.id, event_type="KYC_CASE_CREATED",
            from_status=None, to_status=KycStatus.PENDING_VENDOR,
            created_at=submitted,
        ))
        if status != KycStatus.PENDING_VENDOR:
            db.add(KycCaseEvent(
                kyc_case_id=case.id, event_type="KYC_VENDOR_COMPLETED",
                from_status=KycStatus.PENDING_VENDOR, to_status=KycStatus.NEEDS_REVIEW,
                created_at=submitted + timedelta(minutes=30),
            ))
        if status == KycStatus.APPROVED:
            db.add(KycCaseEvent(
                kyc_case_id=case.id, actor_id=case.decided_by_id,
                event_type="KYC_CASE_APPROVED",
                from_status=KycStatus.NEEDS_REVIEW, to_status=KycStatus.APPROVED,
                created_at=case.decided_at,
            ))
            db.add(AuditEvent(
                actor_id=case.decided_by_id, action="KYC_CASE_APPROVED",
                entity_type="KycCase", entity_id=case.id,
                after={"status": "APPROVED"}, created_at=case.decided_at,
            ))
        elif status == KycStatus.REJECTED:
            db.add(KycCaseEvent(
                kyc_case_id=case.id, actor_id=case.decided_by_id,
                event_type="KYC_CASE_REJECTED",
                from_status=KycStatus.NEEDS_REVIEW, to_status=KycStatus.REJECTED,
                event_metadata={"reason": case.decision_reason},
                created_at=case.decided_at,
            ))
            db.add(AuditEvent(
                actor_id=case.decided_by_id, action="KYC_CASE_REJECTED",
                entity_type="KycCase", entity_id=case.id,
                after={"status": "REJECTED", "reason": case.decision_reason},
                created_at=case.decided_at,
            ))
        cases.append(case)
    db.commit()
    return cases


def seed_payments(db: Session, customers, users) -> list[Payment]:
    providers = [PaymentProvider.STRIPE, PaymentProvider.ADYEN,
                 PaymentProvider.MOCK_PROVIDER]
    payments: list[Payment] = []
    for i in range(44):
        customer = RNG.choice(customers)
        provider = RNG.choice(providers)
        amount = RNG.choice([1999, 4999, 9900, 12500, 25000, 45000, 199900, 250000])
        created = _dt(RNG.uniform(0.1, 60))
        # One deterministic provider-failure payment.
        provider_pid = f"pi_{provider.value.lower()}_{i:04d}"
        if i == 7:
            provider_pid = "pi_mock_0007_FAIL"
            provider = PaymentProvider.MOCK_PROVIDER
        p = Payment(
            id=f"pay_{i:03d}",
            provider=provider,
            provider_payment_id=provider_pid,
            customer_id=customer.id,
            order_id=f"ORD-{10000 + i}",
            amount_minor=amount,
            currency="USD" if i % 8 else RNG.choice(["EUR", "GBP"]),
            status=PaymentStatus.SUCCEEDED,
            payment_method_brand=RNG.choice(CARD_BRANDS),
            payment_method_last4=f"{RNG.randint(0, 9999):04d}",
            created_at=created,
        )
        db.add(p)
        db.flush()
        payments.append(p)

        roll = RNG.random()
        if i in (2, 5):
            p.status = PaymentStatus.DISPUTED
        elif i in (3, 9):
            p.status = PaymentStatus.FAILED
        elif roll < 0.25:
            # Partial refund.
            r_amt = amount // RNG.choice([2, 3, 4])
            r = Refund(
                payment_id=p.id, amount_minor=r_amt, currency=p.currency,
                reason=RNG.choice(list(RefundReason)), status=RefundStatus.SUCCEEDED,
                requested_by_id=users["SUPPORT_AGENT"].id
                if r_amt <= 25000 else users["OPS_REVIEWER"].id,
                idempotency_key=f"seed-refund-{i}-a",
                provider_refund_id=f"re_seed_{i}a",
                created_at=created + timedelta(days=1),
            )
            db.add(r)
            p.status = PaymentStatus.PARTIALLY_REFUNDED
            db.add(AuditEvent(
                actor_id=r.requested_by_id, action="REFUND_SUCCEEDED",
                entity_type="Refund", entity_id=f"pay_{i:03d}",
                after={"amount_minor": r_amt}, created_at=r.created_at,
            ))
        elif roll < 0.35:
            # Full refund.
            r = Refund(
                payment_id=p.id, amount_minor=amount, currency=p.currency,
                reason=RefundReason.DUPLICATE_CHARGE, status=RefundStatus.SUCCEEDED,
                requested_by_id=users["ADMIN"].id,
                idempotency_key=f"seed-refund-{i}-full",
                provider_refund_id=f"re_seed_{i}f",
                created_at=created + timedelta(days=1),
            )
            db.add(r)
            p.status = PaymentStatus.FULLY_REFUNDED
        elif roll < 0.42:
            # A failed refund on the deterministic-failure payment.
            r = Refund(
                payment_id=p.id, amount_minor=min(amount, 5000), currency=p.currency,
                reason=RefundReason.CUSTOMER_REQUEST, status=RefundStatus.FAILED,
                failure_reason="Provider declined the refund (simulated failure).",
                requested_by_id=users["SUPPORT_AGENT"].id,
                idempotency_key=f"seed-refund-{i}-failed",
                created_at=created + timedelta(days=1),
            )
            db.add(r)
    db.commit()
    return payments


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


def seed_integrations(db: Session, customers, kyc_cases, payments) -> None:
    # Persona inquiries mirror KYC cases from the Persona vendor.
    for case in kyc_cases:
        if case.vendor != KycVendor.PERSONA:
            continue
        cust = next((c for c in customers if c.id == case.customer_id), None)
        db.add(IntegrationPersonaInquiry(
            inquiry_id=f"inq_{case.id}",
            reference_id=case.vendor_reference_id,
            status=case.status.value.lower(),
            name_first=cust.first_name if cust else None,
            name_last=cust.last_name if cust else None,
            email_address=cust.email if cust else None,
            country_code=case.country_code,
            risk_score=case.risk_score,
            created_at_source=case.submitted_at,
            raw=case.raw_vendor_payload,
        ))
    # Stripe charges mirror Stripe payments.
    for p in payments:
        if p.provider != PaymentProvider.STRIPE:
            continue
        cust = next((c for c in customers if c.id == p.customer_id), None)
        refunded = sum(
            r.amount_minor for r in p.refunds if r.status == RefundStatus.SUCCEEDED
        )
        db.add(IntegrationStripeCharge(
            charge_id=f"ch_{p.id}",
            payment_intent=p.provider_payment_id,
            amount=p.amount_minor,
            amount_refunded=refunded,
            currency=p.currency.lower(),
            status="succeeded" if p.status != PaymentStatus.FAILED else "failed",
            customer_email=cust.email if cust else None,
            card_brand=p.payment_method_brand,
            card_last4=p.payment_method_last4,
            created_at_source=p.created_at,
            raw={"id": f"ch_{p.id}", "object": "charge",
                 "amount": p.amount_minor, "currency": p.currency.lower()},
        ))
    # LaunchDarkly source flags mirror the flag catalog.
    for i, (key, desc, owner, tags) in enumerate(FLAG_SPECS):
        db.add(IntegrationLaunchDarklyFlag(
            flag_key=key,
            name=desc,
            kind="boolean",
            temporary=("beta" in tags or "deprecated" in tags),
            maintainer=f"{owner}@example.com",
            tags={"tags": tags},
            environments={
                "production": {"on": RNG.random() < 0.4},
                "staging": {"on": RNG.random() < 0.5},
            },
            raw={"key": key, "name": desc},
        ))
    db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        clear(db)
        users = seed_users(db)
        customers = seed_customers(db)
        kyc_cases = seed_kyc(db, customers, users)
        payments = seed_payments(db, customers, users)
        seed_flags(db, users)
        seed_integrations(db, customers, kyc_cases, payments)
        print("Seed complete:")
        print(f"  users={len(users)} customers={len(customers)} "
              f"kyc_cases={len(kyc_cases)} payments={len(payments)} "
              f"flags={len(FLAG_SPECS)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
