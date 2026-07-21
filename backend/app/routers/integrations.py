"""Read-only views over the mock integration source tables.

These endpoints expose the raw upstream records (Persona, Stripe, LaunchDarkly)
so the UI can show "this is the external source of truth we integrate with".
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.integrations import (
    IntegrationLaunchDarklyFlag,
    IntegrationPersonaInquiry,
    IntegrationStripeCharge,
)
from app.models.user import User
from app.serializers import iso

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("")
def list_integrations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    persona = db.scalar(select(func.count()).select_from(IntegrationPersonaInquiry))
    stripe = db.scalar(select(func.count()).select_from(IntegrationStripeCharge))
    ld = db.scalar(select(func.count()).select_from(IntegrationLaunchDarklyFlag))
    return {
        "integrations": [
            {
                "key": "persona",
                "name": "Persona",
                "category": "KYC / Identity Verification",
                "table": "integration_persona_inquiries",
                "record_count": persona or 0,
            },
            {
                "key": "stripe",
                "name": "Stripe",
                "category": "Payments",
                "table": "integration_stripe_charges",
                "record_count": stripe or 0,
            },
            {
                "key": "launchdarkly",
                "name": "LaunchDarkly",
                "category": "Feature Flags",
                "table": "integration_launchdarkly_flags",
                "record_count": ld or 0,
            },
        ]
    }


@router.get("/persona")
def persona_inquiries(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    rows = db.execute(
        select(IntegrationPersonaInquiry).order_by(
            IntegrationPersonaInquiry.created_at_source.desc()
        )
    ).scalars().all()
    return {
        "items": [
            {
                "inquiry_id": r.inquiry_id,
                "reference_id": r.reference_id,
                "status": r.status,
                "name": f"{r.name_first or ''} {r.name_last or ''}".strip(),
                "email": r.email_address,
                "country_code": r.country_code,
                "risk_score": r.risk_score,
                "created_at": iso(r.created_at_source),
            }
            for r in rows
        ]
    }


@router.get("/stripe")
def stripe_charges(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    rows = db.execute(
        select(IntegrationStripeCharge).order_by(
            IntegrationStripeCharge.created_at_source.desc()
        )
    ).scalars().all()
    return {
        "items": [
            {
                "charge_id": r.charge_id,
                "payment_intent": r.payment_intent,
                "amount": r.amount,
                "amount_refunded": r.amount_refunded,
                "currency": r.currency,
                "status": r.status,
                "customer_email": r.customer_email,
                "card_brand": r.card_brand,
                "card_last4": r.card_last4,
                "created_at": iso(r.created_at_source),
            }
            for r in rows
        ]
    }


@router.get("/launchdarkly")
def launchdarkly_flags(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    rows = db.execute(
        select(IntegrationLaunchDarklyFlag).order_by(
            IntegrationLaunchDarklyFlag.flag_key
        )
    ).scalars().all()
    return {
        "items": [
            {
                "flag_key": r.flag_key,
                "name": r.name,
                "kind": r.kind,
                "temporary": r.temporary,
                "maintainer": r.maintainer,
                "tags": r.tags,
                "environments": r.environments,
            }
            for r in rows
        ]
    }
