from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.models.audit import AuditEvent
from app.models.user import User
from app.permissions import require_permission
from app.serializers import audit_row

router = APIRouter(prefix="/api/audit-events", tags=["audit"])


@router.get("")
def list_audit(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    actor_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    require_permission(user, "audit:read")
    stmt = select(AuditEvent).options(selectinload(AuditEvent.actor))
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditEvent.action.ilike(f"%{action}%"))
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if created_from:
        stmt = stmt.where(AuditEvent.created_at >= created_from)
    if created_to:
        stmt = stmt.where(AuditEvent.created_at <= created_to)
    stmt = stmt.order_by(AuditEvent.created_at.desc())

    rows = db.execute(stmt).scalars().all()
    total = len(rows)
    page = rows[offset : offset + limit]
    return {"total": total, "items": [audit_row(e) for e in page]}
