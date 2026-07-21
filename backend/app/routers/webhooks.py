from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import KycStatus
from app.models.kyc import KycCase, KycCaseEvent
from app.models.webhook import ProcessedWebhookEvent
from app.schemas import KycWebhookRequest

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Map inbound vendor statuses to internal KYC statuses.
STATUS_MAP = {
    "completed": KycStatus.NEEDS_REVIEW,
    "needs_review": KycStatus.NEEDS_REVIEW,
    "approved": KycStatus.APPROVED,
    "declined": KycStatus.REJECTED,
    "pending": KycStatus.PENDING_VENDOR,
}


@router.post("/kyc/mock")
def kyc_mock_webhook(
    body: KycWebhookRequest, db: Session = Depends(get_db)
) -> dict:
    """Mock KYC webhook ingestion with idempotent, duplicate-safe processing."""
    # Duplicate events are ignored (idempotency by event id).
    existing = db.scalar(
        select(ProcessedWebhookEvent).where(
            ProcessedWebhookEvent.event_id == body.event_id
        )
    )
    if existing is not None:
        return {"status": "duplicate_ignored", "event_id": body.event_id}

    db.add(ProcessedWebhookEvent(source="kyc_mock", event_id=body.event_id))

    case = db.scalar(
        select(KycCase).where(
            KycCase.vendor_reference_id == body.vendor_reference_id
        )
    )
    updated = False
    if case is not None and case.status not in {
        KycStatus.APPROVED,
        KycStatus.REJECTED,
    }:
        target = STATUS_MAP.get(body.status.lower())
        if target is not None and target != case.status:
            from_status = case.status
            case.status = target
            # Preserve the raw payload for debugging.
            case.raw_vendor_payload = {
                **(case.raw_vendor_payload or {}),
                "last_webhook": body.payload,
            }
            db.add(
                KycCaseEvent(
                    kyc_case_id=case.id,
                    event_type="KYC_WEBHOOK_RECEIVED",
                    from_status=from_status,
                    to_status=target,
                    event_metadata={"event_id": body.event_id,
                                    "vendor_status": body.status},
                )
            )
            updated = True

    db.commit()
    return {
        "status": "processed",
        "event_id": body.event_id,
        "case_updated": updated,
    }
