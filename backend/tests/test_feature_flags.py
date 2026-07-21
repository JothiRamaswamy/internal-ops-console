import pytest

from app.errors import AppError
from app.models.audit import AuditEvent
from app.models.enums import FeatureFlagEnvironment, FeatureFlagType
from app.models.feature_flag import FeatureFlag, FeatureFlagValue, FeatureFlagVersion
from app.services import feature_flag_service
from tests.conftest import flag_config, make_flag


def test_nonprod_update_with_permission_succeeds(db, users):
    flag = make_flag(db, users)
    result = feature_flag_service.set_flag_value(
        db, flag_id=flag.id, environment=FeatureFlagEnvironment.STAGING,
        new_value=flag_config(True, 40), expected_version=1,
        user=users["OPS_REVIEWER"],
    )
    assert result.value["enabled"] is True
    assert result.value["rollout_percentage"] == 40
    assert result.version == 2


def test_unauthorized_prod_update_fails(db, users):
    flag = make_flag(db, users)
    with pytest.raises(AppError) as exc:
        feature_flag_service.set_flag_value(
            db, flag_id=flag.id, environment=FeatureFlagEnvironment.PRODUCTION,
            new_value=flag_config(True), expected_version=1,
            user=users["OPS_REVIEWER"], reason="ship it",
        )
    assert exc.value.code == "FORBIDDEN"


def test_prod_update_without_reason_fails(db, users):
    flag = make_flag(db, users)
    with pytest.raises(AppError) as exc:
        feature_flag_service.set_flag_value(
            db, flag_id=flag.id, environment=FeatureFlagEnvironment.PRODUCTION,
            new_value=flag_config(True), expected_version=1,
            user=users["ADMIN"], reason="",
        )
    assert exc.value.code == "VALIDATION_ERROR"


def test_version_conflict_fails(db, users):
    flag = make_flag(db, users)
    with pytest.raises(AppError) as exc:
        feature_flag_service.set_flag_value(
            db, flag_id=flag.id, environment=FeatureFlagEnvironment.STAGING,
            new_value=flag_config(True), expected_version=99,
            user=users["ADMIN"],
        )
    assert exc.value.code == "VERSION_CONFLICT"


def test_successful_update_creates_version_and_audit(db, users):
    flag = make_flag(db, users)
    feature_flag_service.set_flag_value(
        db, flag_id=flag.id, environment=FeatureFlagEnvironment.PRODUCTION,
        new_value=flag_config(True, 25), expected_version=1,
        user=users["ADMIN"], reason="Gradual rollout",
    )
    versions = db.query(FeatureFlagVersion).filter_by(flag_id=flag.id).all()
    assert any(v.version == 2 and v.reason == "Gradual rollout" for v in versions)
    audits = db.query(AuditEvent).filter_by(entity_id=flag.id).all()
    assert any(a.action == "FEATURE_FLAG_UPDATED" for a in audits)


def test_archived_flag_cannot_be_modified(db, users):
    flag = make_flag(db, users)
    feature_flag_service.archive_flag(db, flag.id, users["ADMIN"])
    with pytest.raises(AppError) as exc:
        feature_flag_service.set_flag_value(
            db, flag_id=flag.id, environment=FeatureFlagEnvironment.STAGING,
            new_value=flag_config(True), expected_version=1, user=users["ADMIN"],
        )
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_invalid_rollout_percentage_rejected(db, users):
    flag = make_flag(db, users)
    with pytest.raises(AppError) as exc:
        feature_flag_service.set_flag_value(
            db, flag_id=flag.id, environment=FeatureFlagEnvironment.STAGING,
            new_value={"enabled": True, "rollout_percentage": 150, "filters": []},
            expected_version=1, user=users["ADMIN"],
        )
    assert exc.value.code == "VALIDATION_ERROR"


def test_invalid_filter_operator_rejected(db, users):
    flag = make_flag(db, users)
    with pytest.raises(AppError) as exc:
        feature_flag_service.set_flag_value(
            db, flag_id=flag.id, environment=FeatureFlagEnvironment.STAGING,
            new_value={
                "enabled": True,
                "rollout_percentage": 50,
                "filters": [{"property": "plan", "operator": "bogus", "value": "x"}],
            },
            expected_version=1, user=users["ADMIN"],
        )
    assert exc.value.code == "VALIDATION_ERROR"


def test_create_flag_seeds_all_environments(db, users):
    flag = feature_flag_service.create_flag(
        db, key="new-checkout", description="New checkout",
        type=FeatureFlagType.BOOLEAN, owner="payments", tags=["billing"],
        user=users["ADMIN"],
    )
    values = db.query(FeatureFlagValue).filter_by(flag_id=flag.id).all()
    assert len(values) == 3
    assert all(v.value == {"enabled": False, "rollout_percentage": 0,
                           "filters": []} for v in values)


def test_create_flag_duplicate_key_rejected(db, users):
    feature_flag_service.create_flag(
        db, key="dupe", description="", type=FeatureFlagType.BOOLEAN,
        owner=None, tags=[], user=users["ADMIN"],
    )
    with pytest.raises(AppError) as exc:
        feature_flag_service.create_flag(
            db, key="dupe", description="", type=FeatureFlagType.BOOLEAN,
            owner=None, tags=[], user=users["ADMIN"],
        )
    assert exc.value.code == "VALIDATION_ERROR"


def test_create_flag_requires_permission(db, users):
    with pytest.raises(AppError) as exc:
        feature_flag_service.create_flag(
            db, key="nope", description="", type=FeatureFlagType.BOOLEAN,
            owner=None, tags=[], user=users["READ_ONLY"],
        )
    assert exc.value.code == "FORBIDDEN"


def test_created_flag_appears(db, users):
    feature_flag_service.create_flag(
        db, key="listed", description="", type=FeatureFlagType.BOOLEAN,
        owner=None, tags=[], user=users["ADMIN"],
    )
    assert db.query(FeatureFlag).filter_by(key="listed").one()
