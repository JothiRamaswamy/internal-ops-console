from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models.customer import Customer
from app.models.enums import KycStatus, KycVendor, RiskLevel
from app.models.kyc import KycCase
from app.models.user import User
from app.permissions import require_permission
from app.schemas import ApproveKycRequest, RejectKycRequest, RequestMoreInfoRequest
from app.serializers import kyc_case_detail, kyc_case_row
from app.services import kyc_service

router = APIRouter(prefix="/api/kyc", tags=["kyc"])


@router.get("")
def list_cases(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status: KycStatus | None = None,
    risk_level: RiskLevel | None = None,
    country: str | None = None,
    vendor: KycVendor | None = None,
    assigned_reviewer_id: str | None = None,
    submitted_from: datetime | None = None,
    submitted_to: datetime | None = None,
    q: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    require_permission(user, "kyc:read")
    stmt = (
        select(KycCase)
        .join(Customer, KycCase.customer_id == Customer.id)
        .options(selectinload(KycCase.customer), selectinload(KycCase.assigned_reviewer))
    )
    if status:
        stmt = stmt.where(KycCase.status == status)
    if risk_level:
        stmt = stmt.where(KycCase.risk_level == risk_level)
    if country:
        stmt = stmt.where(KycCase.country_code == country.upper())
    if vendor:
        stmt = stmt.where(KycCase.vendor == vendor)
    if assigned_reviewer_id:
        if assigned_reviewer_id == "unassigned":
            stmt = stmt.where(KycCase.assigned_reviewer_id.is_(None))
        else:
            stmt = stmt.where(KycCase.assigned_reviewer_id == assigned_reviewer_id)
    if submitted_from:
        stmt = stmt.where(KycCase.submitted_at >= submitted_from)
    if submitted_to:
        stmt = stmt.where(KycCase.submitted_at <= submitted_to)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                KycCase.id.ilike(like),
                Customer.email.ilike(like),
                (Customer.first_name + " " + Customer.last_name).ilike(like),
            )
        )

    all_rows = db.execute(stmt).scalars().all()
    total = len(all_rows)
    ordered = sorted(all_rows, key=lambda c: c.submitted_at)
    page = ordered[offset : offset + limit]
    return {"total": total, "items": [kyc_case_row(c) for c in page]}


@router.get("/summary")
def summary(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    require_permission(user, "kyc:read")
    cases = db.execute(select(KycCase)).scalars().all()
    awaiting = [c for c in cases if c.status == KycStatus.NEEDS_REVIEW]
    high_risk = [
        c for c in awaiting if c.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    ]
    oldest = min((c.submitted_at for c in awaiting), default=None)
    from datetime import timezone

    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    reviewed_today = [
        c for c in cases if c.decided_at and c.decided_at >= today
    ]
    return {
        "awaiting_review": len(awaiting),
        "high_risk": len(high_risk),
        "oldest_unreviewed_at": oldest.isoformat() if oldest else None,
        "reviewed_today": len(reviewed_today),
    }


@router.get("/{case_id}")
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_permission(user, "kyc:read")
    case = db.get(KycCase, case_id)
    if not case:
        from app.errors import AppError

        raise AppError("NOT_FOUND", f"KYC case {case_id} was not found.")
    return kyc_case_detail(case)


@router.post("/{case_id}/assign")
def assign(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    case = kyc_service.assign_case(db, case_id, user, ip=client_ip(request))
    return kyc_case_detail(case)


@router.post("/{case_id}/approve")
def approve(
    case_id: str,
    body: ApproveKycRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    case = kyc_service.approve_case(db, case_id, user, note=body.note,
                                    ip=client_ip(request))
    return kyc_case_detail(case)


@router.post("/{case_id}/reject")
def reject(
    case_id: str,
    body: RejectKycRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    case = kyc_service.reject_case(
        db, case_id, user, reason=body.reason, explanation=body.explanation,
        ip=client_ip(request),
    )
    return kyc_case_detail(case)


@router.post("/{case_id}/request-more-info")
def request_more_info(
    case_id: str,
    body: RequestMoreInfoRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    case = kyc_service.request_more_info(db, case_id, user, note=body.note,
                                         ip=client_ip(request))
    return kyc_case_detail(case)
