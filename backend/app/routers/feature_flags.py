from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import client_ip, get_current_user
from app.errors import AppError
from app.models.feature_flag import FeatureFlag, FeatureFlagValue
from app.models.user import User
from app.permissions import require_permission
from app.schemas import CreateFlagRequest, EvaluateFlagRequest, SetFlagValueRequest
from app.sdk import evaluate as evaluate_flag_config
from app.serializers import flag_detail, flag_row
from app.services import feature_flag_service

router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


@router.post("", status_code=201)
def create_flag(
    body: CreateFlagRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    flag = feature_flag_service.create_flag(
        db,
        key=body.key,
        description=body.description,
        type=body.type,
        owner=body.owner,
        tags=body.tags,
        user=user,
        ip=client_ip(request),
    )
    return flag_detail(flag)


@router.get("")
def list_flags(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    q: str | None = None,
    owner: str | None = None,
    tag: str | None = None,
    include_archived: bool = Query(default=True),
    archived_only: bool = Query(default=False),
) -> dict:
    require_permission(user, "feature_flag:read")
    stmt = select(FeatureFlag).options(
        selectinload(FeatureFlag.values),
    )
    flags = db.execute(stmt).scalars().all()

    def keep(f: FeatureFlag) -> bool:
        if archived_only and f.archived_at is None:
            return False
        if not include_archived and f.archived_at is not None:
            return False
        if owner and f.owner != owner:
            return False
        if tag and tag not in (f.tags or []):
            return False
        if q:
            ql = q.lower()
            if ql not in f.key.lower() and ql not in f.description.lower():
                return False
        return True

    filtered = sorted((f for f in flags if keep(f)), key=lambda f: f.key)
    return {"total": len(filtered), "items": [flag_row(f) for f in filtered]}


@router.get("/{flag_id}")
def get_flag(
    flag_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_permission(user, "feature_flag:read")
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise AppError("NOT_FOUND", f"Feature flag {flag_id} was not found.")
    return flag_detail(flag)


@router.post("/{flag_id}/value")
def set_value(
    flag_id: str,
    body: SetFlagValueRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    feature_flag_service.set_flag_value(
        db,
        flag_id=flag_id,
        environment=body.environment,
        new_value=body.value,
        expected_version=body.expected_version,
        user=user,
        reason=body.reason,
        ip=client_ip(request),
    )
    flag = db.get(FeatureFlag, flag_id)
    return flag_detail(flag)


@router.post("/{flag_id}/evaluate")
def evaluate(
    flag_id: str,
    body: EvaluateFlagRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Evaluate a flag against a context JSON, applying filters + rollout %.

    Uses the same SDK logic (`app.sdk`) that application code would use, so the
    console preview matches production behavior.
    """
    require_permission(user, "feature_flag:read")
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise AppError("NOT_FOUND", f"Feature flag {flag_id} was not found.")

    value_row = db.scalar(
        select(FeatureFlagValue)
        .where(FeatureFlagValue.flag_id == flag_id)
        .where(FeatureFlagValue.environment == body.environment)
    )
    if value_row is None:
        raise AppError(
            "NOT_FOUND", f"No {body.environment.value} value exists for this flag."
        )

    result = evaluate_flag_config(
        value_row.value,
        body.context,
        flag_key=flag.key,
        bucket_by=body.bucket_by,
    )
    return {
        "flag_key": flag.key,
        "environment": body.environment.value,
        "enabled": result.enabled,
        "reason": result.reason,
    }


@router.post("/{flag_id}/archive")
def archive(
    flag_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    feature_flag_service.archive_flag(db, flag_id, user, ip=client_ip(request))
    flag = db.get(FeatureFlag, flag_id)
    return flag_detail(flag)


@router.post("/{flag_id}/restore")
def restore(
    flag_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    feature_flag_service.restore_flag(db, flag_id, user, ip=client_ip(request))
    flag = db.get(FeatureFlag, flag_id)
    return flag_detail(flag)
