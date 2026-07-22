from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import (
    FeatureFlagEnvironment,
    KycStatus,
    RefundStatus,
    RiskLevel,
)
from app.models.feature_flag import FeatureFlagValue, FeatureFlagVersion
from app.models.kyc import KycCase
from app.models.payment import Refund


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_overview(db: Session) -> dict:
    today = _start_of_today()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    awaiting_review = db.scalar(
        select(func.count())
        .select_from(KycCase)
        .where(KycCase.status == KycStatus.NEEDS_REVIEW)
    )
    high_risk = db.scalar(
        select(func.count())
        .select_from(KycCase)
        .where(KycCase.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]))
        .where(KycCase.status == KycStatus.NEEDS_REVIEW)
    )

    refund_volume_today = db.scalar(
        select(func.coalesce(func.sum(Refund.amount_minor), 0))
        .where(Refund.status == RefundStatus.SUCCEEDED)
        .where(Refund.created_at >= today)
    )
    failed_refunds = db.scalar(
        select(func.count())
        .select_from(Refund)
        .where(Refund.status == RefundStatus.FAILED)
    )

    prod_values = (
        db.execute(
            select(FeatureFlagValue.value).where(
                FeatureFlagValue.environment == FeatureFlagEnvironment.PRODUCTION
            )
        )
        .scalars()
        .all()
    )
    prod_flags_enabled = sum(
        1 for v in prod_values if isinstance(v, dict) and v.get("enabled") is True
    )
    prod_changes_week = db.scalar(
        select(func.count())
        .select_from(FeatureFlagVersion)
        .where(FeatureFlagVersion.environment == FeatureFlagEnvironment.PRODUCTION)
        .where(FeatureFlagVersion.created_at >= week_ago)
    )

    return {
        "kyc_awaiting_review": awaiting_review or 0,
        "kyc_high_risk": high_risk or 0,
        "refund_volume_today_minor": refund_volume_today or 0,
        "failed_refunds": failed_refunds or 0,
        "prod_flags_enabled": prod_flags_enabled or 0,
        "prod_flag_changes_last_7d": prod_changes_week or 0,
    }
