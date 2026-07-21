from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def record_audit(
    db: Session,
    *,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    """Append an immutable audit event.

    Must be called inside the same transaction as the mutation it records so the
    audit trail can never drift from the underlying change.
    """
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        event_metadata=metadata,
        ip_address=ip_address,
    )
    db.add(event)
    db.flush()
    return event
