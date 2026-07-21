from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.enums import KycStatus
from app.models.kyc import KycCase, KycCaseEvent
from app.models.user import User
from app.permissions import require_permission
from app.services.audit_service import record_audit

# Reviewer decisions are only valid from NEEDS_REVIEW.
DECIDABLE_FROM = {KycStatus.NEEDS_REVIEW}
TERMINAL = {KycStatus.APPROVED, KycStatus.REJECTED}

REJECTION_REASONS = {
    "DOCUMENT_UNVERIFIABLE",
    "IDENTITY_MISMATCH",
    "SUSPECTED_FRAUD",
    "WATCHLIST_MATCH",
    "UNSUPPORTED_COUNTRY",
    "DUPLICATE_ACCOUNT",
    "OTHER",
}


def _get_case(db: Session, case_id: str) -> KycCase:
    case = db.get(KycCase, case_id)
    if not case:
        raise AppError("NOT_FOUND", f"KYC case {case_id} was not found.")
    return case


def _add_event(
    db: Session,
    case: KycCase,
    actor: User | None,
    event_type: str,
    from_status: KycStatus | None,
    to_status: KycStatus | None,
    metadata: dict | None = None,
) -> None:
    db.add(
        KycCaseEvent(
            kyc_case_id=case.id,
            actor_id=actor.id if actor else None,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            event_metadata=metadata,
        )
    )


def assign_case(
    db: Session, case_id: str, user: User, ip: str | None = None
) -> KycCase:
    require_permission(user, "kyc:review")
    case = _get_case(db, case_id)
    if case.status in TERMINAL:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            "Cannot assign a case that has already been decided.",
            {"status": case.status.value},
        )
    before = {"assigned_reviewer_id": case.assigned_reviewer_id}
    case.assigned_reviewer_id = user.id
    _add_event(db, case, user, "KYC_CASE_ASSIGNED", case.status, case.status,
               {"assigned_reviewer_id": user.id})
    record_audit(
        db,
        actor_id=user.id,
        action="KYC_CASE_ASSIGNED",
        entity_type="KycCase",
        entity_id=case.id,
        before=before,
        after={"assigned_reviewer_id": user.id},
        ip_address=ip,
    )
    db.commit()
    db.refresh(case)
    return case


def _ensure_decidable(case: KycCase) -> None:
    if case.status in TERMINAL:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            "This case has already reached a terminal decision.",
            {"status": case.status.value},
        )
    if case.status not in DECIDABLE_FROM:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            "Only cases awaiting review can be approved or rejected.",
            {"status": case.status.value},
        )


def approve_case(
    db: Session, case_id: str, user: User, note: str | None = None, ip: str | None = None
) -> KycCase:
    require_permission(user, "kyc:review")
    case = _get_case(db, case_id)
    _ensure_decidable(case)
    before = {"status": case.status.value}
    case.status = KycStatus.APPROVED
    case.decision_note = note
    case.decided_at = datetime.now(timezone.utc)
    case.decided_by_id = user.id
    _add_event(db, case, user, "KYC_CASE_APPROVED", KycStatus.NEEDS_REVIEW,
               KycStatus.APPROVED, {"note": note})
    record_audit(
        db,
        actor_id=user.id,
        action="KYC_CASE_APPROVED",
        entity_type="KycCase",
        entity_id=case.id,
        before=before,
        after={"status": case.status.value, "note": note},
        ip_address=ip,
    )
    db.commit()
    db.refresh(case)
    return case


def reject_case(
    db: Session,
    case_id: str,
    user: User,
    reason: str,
    explanation: str | None = None,
    ip: str | None = None,
) -> KycCase:
    require_permission(user, "kyc:review")
    if not reason or reason not in REJECTION_REASONS:
        raise AppError(
            "VALIDATION_ERROR",
            "A valid rejection reason is required.",
            {"allowed": sorted(REJECTION_REASONS)},
        )
    case = _get_case(db, case_id)
    _ensure_decidable(case)
    before = {"status": case.status.value}
    case.status = KycStatus.REJECTED
    case.decision_reason = reason
    case.decision_note = explanation
    case.decided_at = datetime.now(timezone.utc)
    case.decided_by_id = user.id
    _add_event(db, case, user, "KYC_CASE_REJECTED", KycStatus.NEEDS_REVIEW,
               KycStatus.REJECTED, {"reason": reason, "explanation": explanation})
    record_audit(
        db,
        actor_id=user.id,
        action="KYC_CASE_REJECTED",
        entity_type="KycCase",
        entity_id=case.id,
        before=before,
        after={"status": case.status.value, "reason": reason,
               "explanation": explanation},
        ip_address=ip,
    )
    db.commit()
    db.refresh(case)
    return case


def request_more_info(
    db: Session, case_id: str, user: User, note: str | None = None, ip: str | None = None
) -> KycCase:
    require_permission(user, "kyc:review")
    case = _get_case(db, case_id)
    if case.status not in {KycStatus.NEEDS_REVIEW}:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            "Only cases awaiting review can be sent back for more information.",
            {"status": case.status.value},
        )
    before = {"status": case.status.value}
    case.status = KycStatus.REQUESTED_MORE_INFO
    _add_event(db, case, user, "KYC_MORE_INFO_REQUESTED", KycStatus.NEEDS_REVIEW,
               KycStatus.REQUESTED_MORE_INFO, {"note": note})
    record_audit(
        db,
        actor_id=user.id,
        action="KYC_MORE_INFO_REQUESTED",
        entity_type="KycCase",
        entity_id=case.id,
        before=before,
        after={"status": case.status.value, "note": note},
        ip_address=ip,
    )
    db.commit()
    db.refresh(case)
    return case
