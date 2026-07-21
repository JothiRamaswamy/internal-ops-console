"""Integration health + the inbound sync/ETL trigger.

The console integrates two external sources — Persona (KYC) and Stripe
(payments). Feature flags are console-owned and have no integration. This
router reports connection health and sync freshness (last / next sync),
exposes the manual sync trigger, and returns a sample of the most-recent rows
landed in each integration's staging table.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models.audit import AuditEvent
from app.models.enums import UserRole
from app.models.integrations import (
    IntegrationPersonaInquiry,
    IntegrationStripeCharge,
)
from app.models.user import User
from app.serializers import iso
from app.services import sync_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Roles allowed to trigger a manual inbound sync.
SYNC_ROLES = {UserRole.ADMIN, UserRole.OPS_REVIEWER}

# Nominal cadence for the scheduled sync in production; used to derive the
# "next sync" estimate shown on the health page.
SYNC_INTERVAL = timedelta(minutes=15)


def _last_synced_at(db: Session) -> datetime | None:
    return db.scalar(
        select(func.max(AuditEvent.created_at)).where(
            AuditEvent.action == "INTEGRATION_SYNCED"
        )
    )


@router.post("/sync")
def trigger_sync(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    """Run the inbound sync/ETL: integration_* source tables -> domain tables."""
    if user.role not in SYNC_ROLES:
        raise AppError(
            "FORBIDDEN",
            "You do not have permission to run an integration sync.",
            {"role": user.role.value},
        )
    result = sync_service.sync_all(db)
    record_audit(
        db,
        actor_id=user.id,
        action="INTEGRATION_SYNCED",
        entity_type="Integration",
        entity_id="all",
        after=result,
    )
    db.commit()
    return {"result": result}


@router.get("")
def list_integrations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    """Health + sync-freshness for each connected integration."""
    persona = db.scalar(select(func.count()).select_from(IntegrationPersonaInquiry))
    stripe = db.scalar(select(func.count()).select_from(IntegrationStripeCharge))
    last = _last_synced_at(db)
    next_sync = (last + SYNC_INTERVAL) if last else None

    def entry(key: str, name: str, category: str, count: int | None) -> dict:
        return {
            "key": key,
            "name": name,
            "category": category,
            "status": "connected",
            "record_count": count or 0,
            "last_synced_at": iso(last),
            "next_sync_at": iso(next_sync),
        }

    return {
        "integrations": [
            entry("persona", "Persona", "KYC / Identity Verification", persona),
            entry("stripe", "Stripe", "Payments", stripe),
        ],
        "last_synced_at": iso(last),
        "next_sync_at": iso(next_sync),
        "sync_interval_minutes": int(SYNC_INTERVAL.total_seconds() // 60),
    }


@router.get("/persona")
def persona_inquiries(
    limit: int = 8,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Most-recent Persona inquiries landed in the KYC staging table."""
    rows = db.scalars(
        select(IntegrationPersonaInquiry)
        .order_by(IntegrationPersonaInquiry.created_at_source.desc())
        .limit(limit)
    ).all()
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
    limit: int = 8,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Most-recent Stripe charges landed in the payments staging table."""
    rows = db.scalars(
        select(IntegrationStripeCharge)
        .order_by(IntegrationStripeCharge.created_at_source.desc())
        .limit(limit)
    ).all()
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
