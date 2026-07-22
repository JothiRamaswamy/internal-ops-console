"""Unit tests for the dependency-free feature-flag SDK (app.sdk)."""

from app.sdk import Evaluation, FeatureFlagClient, evaluate, is_enabled


def cfg(enabled=True, rollout_percentage=100, filters=None):
    return {
        "enabled": enabled,
        "rollout_percentage": rollout_percentage,
        "filters": filters or [],
    }


def test_disabled_flag_is_off():
    result = evaluate(cfg(enabled=False), {}, flag_key="f")
    assert result.enabled is False
    assert "disabled" in result.reason.lower()


def test_enabled_full_rollout_no_filters_is_on():
    assert is_enabled(cfg(), {}, flag_key="f") is True


def test_zero_rollout_is_off_even_when_enabled():
    assert is_enabled(cfg(rollout_percentage=0), {"distinct_id": "u1"},
                      flag_key="f") is False


def test_equals_filter_matches_and_blocks():
    c = cfg(filters=[{"property": "plan", "operator": "equals",
                      "value": "enterprise"}])
    assert is_enabled(c, {"plan": "enterprise"}, flag_key="f") is True
    assert is_enabled(c, {"plan": "free"}, flag_key="f") is False
    assert is_enabled(c, {}, flag_key="f") is False


def test_not_equals_filter():
    c = cfg(filters=[{"property": "plan", "operator": "not_equals",
                      "value": "free"}])
    assert is_enabled(c, {"plan": "enterprise"}, flag_key="f") is True
    assert is_enabled(c, {"plan": "free"}, flag_key="f") is False


def test_contains_filter_string_and_list():
    string_cfg = cfg(filters=[{"property": "email", "operator": "contains",
                               "value": "@acme.com"}])
    assert is_enabled(string_cfg, {"email": "a@acme.com"}, flag_key="f") is True
    assert is_enabled(string_cfg, {"email": "a@other.com"}, flag_key="f") is False

    list_cfg = cfg(filters=[{"property": "roles", "operator": "contains",
                             "value": "admin"}])
    assert is_enabled(list_cfg, {"roles": ["admin", "ops"]}, flag_key="f") is True
    assert is_enabled(list_cfg, {"roles": ["ops"]}, flag_key="f") is False


def test_in_filter_list_and_csv():
    list_cfg = cfg(filters=[{"property": "country", "operator": "in",
                             "value": ["US", "CA"]}])
    assert is_enabled(list_cfg, {"country": "US"}, flag_key="f") is True
    assert is_enabled(list_cfg, {"country": "GB"}, flag_key="f") is False

    csv_cfg = cfg(filters=[{"property": "country", "operator": "in",
                            "value": "US, CA"}])
    assert is_enabled(csv_cfg, {"country": "CA"}, flag_key="f") is True


def test_multiple_filters_are_anded():
    c = cfg(filters=[
        {"property": "plan", "operator": "equals", "value": "enterprise"},
        {"property": "country", "operator": "in", "value": ["US"]},
    ])
    assert is_enabled(c, {"plan": "enterprise", "country": "US"},
                      flag_key="f") is True
    assert is_enabled(c, {"plan": "enterprise", "country": "GB"},
                      flag_key="f") is False


def test_coerced_equality_across_types():
    c = cfg(filters=[{"property": "tier", "operator": "equals", "value": 2}])
    assert is_enabled(c, {"tier": "2"}, flag_key="f") is True
    # bools never coerce to numbers/strings
    b = cfg(filters=[{"property": "flag", "operator": "equals", "value": 1}])
    assert is_enabled(b, {"flag": True}, flag_key="f") is False


def test_partial_rollout_is_deterministic():
    c = cfg(rollout_percentage=50)
    first = is_enabled(c, {"distinct_id": "user-123"}, flag_key="checkout")
    second = is_enabled(c, {"distinct_id": "user-123"}, flag_key="checkout")
    assert first == second


def test_partial_rollout_requires_identity():
    result = evaluate(cfg(rollout_percentage=50), {}, flag_key="f")
    assert result.enabled is False
    assert "identity" in result.reason.lower()


def test_partial_rollout_distribution_is_roughly_pct():
    c = cfg(rollout_percentage=30)
    n = 2000
    on = sum(
        is_enabled(c, {"distinct_id": f"user-{i}"}, flag_key="rollout-test")
        for i in range(n)
    )
    # Deterministic hashing should land near 30% (allow generous tolerance).
    assert 0.24 * n < on < 0.36 * n


def test_bucket_by_override():
    c = cfg(rollout_percentage=50)
    # Same account bucketed consistently regardless of per-user id.
    a = evaluate(c, {"account_id": "acct-9", "distinct_id": "x"},
                 flag_key="f", bucket_by="account_id")
    b = evaluate(c, {"account_id": "acct-9", "distinct_id": "y"},
                 flag_key="f", bucket_by="account_id")
    assert a.enabled == b.enabled


def test_legacy_boolean_config():
    assert is_enabled(True, {}, flag_key="f") is True
    assert is_enabled(False, {}, flag_key="f") is False


def test_client_evaluates_by_key_and_handles_unknown():
    client = FeatureFlagClient({
        "new-billing": cfg(filters=[{"property": "plan", "operator": "equals",
                                     "value": "enterprise"}]),
    })
    assert client.is_enabled("new-billing", {"plan": "enterprise"}) is True
    assert client.is_enabled("new-billing", {"plan": "free"}) is False
    unknown = client.evaluate("does-not-exist", {})
    assert isinstance(unknown, Evaluation)
    assert unknown.enabled is False
    assert "unknown" in unknown.reason.lower()
