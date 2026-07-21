from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.enums import FeatureFlagEnvironment, FeatureFlagType
from app.models.feature_flag import FeatureFlag, FeatureFlagValue, FeatureFlagVersion
from app.models.user import User
from app.permissions import has_permission, require_permission
from app.services.audit_service import record_audit

# Supported targeting operators (PostHog-style property filters).
ALLOWED_OPERATORS = {"equals", "not_equals", "contains", "in"}


def default_config() -> dict[str, Any]:
    """A freshly created flag is off everywhere with 0% rollout."""
    return {"enabled": False, "rollout_percentage": 0, "filters": []}


def normalize_config(raw: Any) -> dict[str, Any]:
    """Validate and normalize a per-environment flag config.

    Shape: {enabled: bool, rollout_percentage: 0-100, filters: [{property,
    operator, value}]}. Legacy boolean values are upgraded transparently.
    """
    if isinstance(raw, bool):
        return {
            "enabled": raw,
            "rollout_percentage": 100 if raw else 0,
            "filters": [],
        }
    if not isinstance(raw, dict):
        raise AppError("VALIDATION_ERROR", "Flag value must be a config object.")

    enabled = bool(raw.get("enabled", False))
    pct = raw.get("rollout_percentage", 100 if enabled else 0)
    if isinstance(pct, bool) or not isinstance(pct, int) or pct < 0 or pct > 100:
        raise AppError(
            "VALIDATION_ERROR",
            "rollout_percentage must be an integer between 0 and 100.",
        )

    filters_in = raw.get("filters") or []
    if not isinstance(filters_in, list):
        raise AppError("VALIDATION_ERROR", "filters must be a list.")
    filters: list[dict[str, Any]] = []
    for f in filters_in:
        if not isinstance(f, dict):
            raise AppError("VALIDATION_ERROR", "Each filter must be an object.")
        prop = str(f.get("property", "")).strip()
        op = str(f.get("operator", "")).strip()
        if not prop:
            raise AppError("VALIDATION_ERROR", "Each filter needs a property.")
        if op not in ALLOWED_OPERATORS:
            raise AppError(
                "VALIDATION_ERROR",
                f"Unsupported filter operator '{op}'.",
            )
        filters.append({"property": prop, "operator": op, "value": f.get("value", "")})

    return {"enabled": enabled, "rollout_percentage": pct, "filters": filters}


def _get_flag(db: Session, flag_id: str) -> FeatureFlag:
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise AppError("NOT_FOUND", f"Feature flag {flag_id} was not found.")
    return flag


def create_flag(
    db: Session,
    *,
    key: str,
    description: str,
    type: FeatureFlagType,
    owner: str | None,
    tags: list[str] | None,
    user: User,
    ip: str | None = None,
) -> FeatureFlag:
    require_permission(user, "feature_flag:write_nonprod")
    key = (key or "").strip()
    if not key:
        raise AppError("VALIDATION_ERROR", "A flag key is required.")
    if db.scalar(select(FeatureFlag).where(FeatureFlag.key == key)) is not None:
        raise AppError(
            "VALIDATION_ERROR", f"A flag with key '{key}' already exists."
        )

    flag = FeatureFlag(
        key=key,
        description=(description or "").strip(),
        type=type,
        owner=(owner or user.name).strip(),
        tags=tags or [],
    )
    db.add(flag)
    db.flush()

    config = default_config()
    for env in FeatureFlagEnvironment:
        db.add(
            FeatureFlagValue(
                flag_id=flag.id,
                environment=env,
                value=config,
                version=1,
                updated_by_id=user.id,
            )
        )
        db.add(
            FeatureFlagVersion(
                flag_id=flag.id,
                environment=env,
                previous_value=None,
                new_value=config,
                version=1,
                reason="Flag created",
                changed_by_id=user.id,
            )
        )

    record_audit(
        db,
        actor_id=user.id,
        action="FEATURE_FLAG_CREATED",
        entity_type="FeatureFlag",
        entity_id=flag.id,
        after={"key": flag.key, "type": flag.type.value},
        ip_address=ip,
    )
    db.commit()
    db.refresh(flag)
    return flag


def _require_env_permission(user: User, environment: FeatureFlagEnvironment) -> None:
    if environment == FeatureFlagEnvironment.PRODUCTION:
        require_permission(user, "feature_flag:write_prod")
    else:
        require_permission(user, "feature_flag:write_nonprod")


def set_flag_value(
    db: Session,
    *,
    flag_id: str,
    environment: FeatureFlagEnvironment,
    new_value,
    expected_version: int,
    user: User,
    reason: str | None = None,
    ip: str | None = None,
) -> FeatureFlagValue:
    _require_env_permission(user, environment)
    flag = _get_flag(db, flag_id)

    if flag.archived_at is not None:
        raise AppError(
            "INVALID_STATE_TRANSITION",
            "Archived flags cannot be modified. Restore the flag first.",
        )

    if environment == FeatureFlagEnvironment.PRODUCTION and not (reason and reason.strip()):
        raise AppError(
            "VALIDATION_ERROR", "A change reason is required for production changes."
        )

    new_value = normalize_config(new_value)

    value_row = db.scalar(
        select(FeatureFlagValue)
        .where(FeatureFlagValue.flag_id == flag_id)
        .where(FeatureFlagValue.environment == environment)
        .with_for_update()
    )
    if value_row is None:
        raise AppError(
            "NOT_FOUND",
            f"No {environment.value} value exists for this flag.",
        )

    # Optimistic concurrency: reject stale writes.
    if value_row.version != expected_version:
        raise AppError(
            "VERSION_CONFLICT",
            "This flag was changed by someone else. Reload and try again.",
            {"expected_version": expected_version, "current_version": value_row.version},
        )

    previous_value = value_row.value
    value_row.value = new_value
    value_row.version = value_row.version + 1
    value_row.updated_by_id = user.id
    value_row.updated_at = datetime.now(timezone.utc)

    db.add(
        FeatureFlagVersion(
            flag_id=flag.id,
            environment=environment,
            previous_value=previous_value,
            new_value=new_value,
            version=value_row.version,
            reason=reason or "",
            changed_by_id=user.id,
        )
    )

    record_audit(
        db,
        actor_id=user.id,
        action="FEATURE_FLAG_UPDATED",
        entity_type="FeatureFlag",
        entity_id=flag.id,
        before={"environment": environment.value, "value": previous_value},
        after={"environment": environment.value, "value": new_value,
               "version": value_row.version},
        metadata={"reason": reason} if reason else None,
        ip_address=ip,
    )

    db.commit()
    db.refresh(value_row)
    return value_row


def archive_flag(
    db: Session, flag_id: str, user: User, ip: str | None = None
) -> FeatureFlag:
    require_permission(user, "feature_flag:write_prod")
    flag = _get_flag(db, flag_id)
    if flag.archived_at is not None:
        return flag
    flag.archived_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor_id=user.id,
        action="FEATURE_FLAG_ARCHIVED",
        entity_type="FeatureFlag",
        entity_id=flag.id,
        after={"archived_at": flag.archived_at.isoformat()},
        ip_address=ip,
    )
    db.commit()
    db.refresh(flag)
    return flag


def restore_flag(
    db: Session, flag_id: str, user: User, ip: str | None = None
) -> FeatureFlag:
    require_permission(user, "feature_flag:write_prod")
    flag = _get_flag(db, flag_id)
    if flag.archived_at is None:
        return flag
    flag.archived_at = None
    record_audit(
        db,
        actor_id=user.id,
        action="FEATURE_FLAG_RESTORED",
        entity_type="FeatureFlag",
        entity_id=flag.id,
        after={"archived_at": None},
        ip_address=ip,
    )
    db.commit()
    db.refresh(flag)
    return flag


def can_write_environment(user: User, environment: FeatureFlagEnvironment) -> bool:
    if environment == FeatureFlagEnvironment.PRODUCTION:
        return has_permission(user, "feature_flag:write_prod")
    return has_permission(user, "feature_flag:write_nonprod")
