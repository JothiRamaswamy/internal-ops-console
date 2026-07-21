from typing import Any

from app.models.audit import AuditEvent
from app.models.customer import Customer
from app.models.feature_flag import (
    FeatureFlag,
    FeatureFlagValue,
    FeatureFlagVersion,
)
from app.models.kyc import KycCase, KycCaseEvent
from app.models.payment import Payment, Refund
from app.models.user import User
from app.services.refund_service import (
    refunded_minor,
    remaining_refundable_minor,
)


def iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def user_summary(user: User | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {"id": user.id, "name": user.name, "email": user.email,
            "role": user.role.value}


def customer_summary(c: Customer | None) -> dict[str, Any] | None:
    if not c:
        return None
    return {
        "id": c.id,
        "email": c.email,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "full_name": f"{c.first_name} {c.last_name}",
        "date_of_birth": iso(c.date_of_birth) if c.date_of_birth else None,
        "country_code": c.country_code,
        "created_at": iso(c.created_at),
    }


def kyc_case_row(case: KycCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "customer": customer_summary(case.customer),
        "vendor": case.vendor.value,
        "vendor_reference_id": case.vendor_reference_id,
        "status": case.status.value,
        "risk_level": case.risk_level.value,
        "risk_score": case.risk_score,
        "country_code": case.country_code,
        "submitted_at": iso(case.submitted_at),
        "assigned_reviewer": user_summary(case.assigned_reviewer),
    }


def kyc_case_detail(case: KycCase) -> dict[str, Any]:
    row = kyc_case_row(case)
    row.update(
        {
            "decision_reason": case.decision_reason,
            "decision_note": case.decision_note,
            "decided_at": iso(case.decided_at),
            "decided_by": user_summary(case.decided_by),
            "raw_vendor_payload": case.raw_vendor_payload,
            "events": [kyc_event(e) for e in case.events],
        }
    )
    return row


def kyc_event(e: KycCaseEvent) -> dict[str, Any]:
    return {
        "id": e.id,
        "event_type": e.event_type,
        "actor": user_summary(e.actor),
        "from_status": e.from_status.value if e.from_status else None,
        "to_status": e.to_status.value if e.to_status else None,
        "metadata": e.event_metadata,
        "created_at": iso(e.created_at),
    }


def refund_row(r: Refund) -> dict[str, Any]:
    return {
        "id": r.id,
        "amount_minor": r.amount_minor,
        "currency": r.currency,
        "reason": r.reason.value,
        "note": r.note,
        "status": r.status.value,
        "failure_reason": r.failure_reason,
        "provider_refund_id": r.provider_refund_id,
        "requested_by": user_summary(r.requested_by),
        "created_at": iso(r.created_at),
    }


def payment_row(p: Payment) -> dict[str, Any]:
    return {
        "id": p.id,
        "provider": p.provider.value,
        "provider_payment_id": p.provider_payment_id,
        "customer": customer_summary(p.customer),
        "order_id": p.order_id,
        "amount_minor": p.amount_minor,
        "refunded_minor": refunded_minor(p),
        "remaining_refundable_minor": remaining_refundable_minor(p),
        "currency": p.currency,
        "status": p.status.value,
        "payment_method_brand": p.payment_method_brand,
        "payment_method_last4": p.payment_method_last4,
        "created_at": iso(p.created_at),
    }


def payment_detail(p: Payment) -> dict[str, Any]:
    row = payment_row(p)
    row["refunds"] = [refund_row(r) for r in p.refunds]
    return row


def flag_value(v: FeatureFlagValue) -> dict[str, Any]:
    return {
        "environment": v.environment.value,
        "value": v.value,
        "version": v.version,
        "updated_by": user_summary(v.updated_by),
        "updated_at": iso(v.updated_at),
    }


def flag_version(v: FeatureFlagVersion) -> dict[str, Any]:
    return {
        "id": v.id,
        "environment": v.environment.value,
        "previous_value": v.previous_value,
        "new_value": v.new_value,
        "version": v.version,
        "reason": v.reason,
        "changed_by": user_summary(v.changed_by),
        "created_at": iso(v.created_at),
    }


def flag_row(f: FeatureFlag) -> dict[str, Any]:
    values = {v.environment.value: flag_value(v) for v in f.values}
    return {
        "id": f.id,
        "key": f.key,
        "description": f.description,
        "type": f.type.value,
        "owner": f.owner,
        "tags": list(f.tags or []),
        "archived_at": iso(f.archived_at),
        "is_archived": f.archived_at is not None,
        "values": values,
        "updated_at": iso(f.updated_at),
    }


def flag_detail(f: FeatureFlag) -> dict[str, Any]:
    row = flag_row(f)
    row["versions"] = [flag_version(v) for v in f.versions]
    return row


def audit_row(e: AuditEvent) -> dict[str, Any]:
    return {
        "id": e.id,
        "actor": user_summary(e.actor),
        "action": e.action,
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "before": e.before,
        "after": e.after,
        "metadata": e.event_metadata,
        "ip_address": e.ip_address,
        "created_at": iso(e.created_at),
    }
