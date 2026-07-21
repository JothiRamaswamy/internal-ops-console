import pytest

from app.errors import AppError
from app.models.enums import KycStatus, KycVendor, RiskLevel
from app.models.kyc import KycCase
from app.models.audit import AuditEvent
from app.services import kyc_service


def make_case(db, customer, status=KycStatus.NEEDS_REVIEW) -> KycCase:
    case = KycCase(
        customer_id=customer.id,
        vendor=KycVendor.MOCK_VENDOR,
        vendor_reference_id=f"ref-{status.value}",
        status=status,
        risk_level=RiskLevel.LOW,
        risk_score=10,
        country_code="US",
        submitted_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        raw_vendor_payload={},
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def test_valid_approval(db, users, customer):
    case = make_case(db, customer)
    result = kyc_service.approve_case(db, case.id, users["OPS_REVIEWER"], note="ok")
    assert result.status == KycStatus.APPROVED
    assert result.decided_by_id == users["OPS_REVIEWER"].id


def test_valid_rejection(db, users, customer):
    case = make_case(db, customer)
    result = kyc_service.reject_case(
        db, case.id, users["OPS_REVIEWER"], reason="IDENTITY_MISMATCH"
    )
    assert result.status == KycStatus.REJECTED
    assert result.decision_reason == "IDENTITY_MISMATCH"


def test_rejection_without_reason_fails(db, users, customer):
    case = make_case(db, customer)
    with pytest.raises(AppError) as exc:
        kyc_service.reject_case(db, case.id, users["OPS_REVIEWER"], reason="")
    assert exc.value.code == "VALIDATION_ERROR"


def test_cannot_approve_rejected_case(db, users, customer):
    case = make_case(db, customer, status=KycStatus.REJECTED)
    with pytest.raises(AppError) as exc:
        kyc_service.approve_case(db, case.id, users["OPS_REVIEWER"])
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_cannot_modify_terminal_case(db, users, customer):
    case = make_case(db, customer, status=KycStatus.APPROVED)
    with pytest.raises(AppError) as exc:
        kyc_service.reject_case(
            db, case.id, users["OPS_REVIEWER"], reason="SUSPECTED_FRAUD"
        )
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_audit_event_is_produced(db, users, customer):
    case = make_case(db, customer)
    kyc_service.approve_case(db, case.id, users["OPS_REVIEWER"])
    events = db.query(AuditEvent).filter_by(entity_id=case.id).all()
    assert any(e.action == "KYC_CASE_APPROVED" for e in events)


def test_readonly_cannot_review(db, users, customer):
    case = make_case(db, customer)
    with pytest.raises(AppError) as exc:
        kyc_service.approve_case(db, case.id, users["READ_ONLY"])
    assert exc.value.code == "FORBIDDEN"
