"""Feature-flag evaluation SDK.

Pure, dependency-free logic that decides whether a flag is ON for a given
evaluation *context* (an arbitrary JSON object describing the caller — the
current user, account, request, etc.). It mirrors the console's stored
per-environment config shape:

    {
        "enabled": bool,
        "rollout_percentage": int,   # 0-100
        "filters": [
            {"property": str,
             "operator": "equals" | "not_equals" | "contains" | "in",
             "value": Any},
            ...
        ],
    }

A flag evaluates to ``True`` when, in order:

1. it is ``enabled``; and
2. *every* targeting filter matches the context (logical AND); and
3. the context falls inside the rollout bucket.

Rollout bucketing is deterministic: the same flag key + identity always land in
the same bucket, so a percentage rollout is stable across calls and consistent
per user. The identity is read from the context (``distinct_id`` by default,
with common fallbacks); this is the standard "sticky" percentage-rollout
technique used by tools like PostHog/LaunchDarkly.

Usage:

    from app.sdk import evaluate, is_enabled, FeatureFlagClient

    config = {"enabled": True, "rollout_percentage": 50,
              "filters": [{"property": "plan", "operator": "equals",
                           "value": "enterprise"}]}
    is_enabled(config, {"plan": "enterprise", "distinct_id": "user-42"},
               flag_key="new-billing")  # -> True/False

    client = FeatureFlagClient({"new-billing": config})
    client.is_enabled("new-billing", {"plan": "enterprise",
                                      "distinct_id": "user-42"})
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SUPPORTED_OPERATORS = ("equals", "not_equals", "contains", "in")

# Context keys tried, in order, when no explicit bucketing key is given.
DEFAULT_IDENTITY_KEYS = ("distinct_id", "user_id", "userId", "id", "key")

# 60 bits of the digest → a stable fraction in [0, 1).
_BUCKET_HEX_LEN = 15
_BUCKET_MAX = float(16**_BUCKET_HEX_LEN)


@dataclass(frozen=True)
class Evaluation:
    """The outcome of evaluating a flag, with a human-readable reason."""

    enabled: bool
    reason: str


def _coerced_equals(actual: Any, target: Any) -> bool:
    # Booleans only ever match booleans (avoid True == 1 surprises).
    if isinstance(actual, bool) or isinstance(target, bool):
        return isinstance(actual, bool) and isinstance(target, bool) and actual == target
    if actual == target:
        return True
    if actual is None or target is None:
        return False
    return str(actual) == str(target)


def _as_membership(target: Any) -> list[Any]:
    """Normalize an ``in`` filter's value to a list of candidates."""
    if isinstance(target, (list, tuple, set)):
        return list(target)
    if isinstance(target, str):
        return [part.strip() for part in target.split(",") if part.strip()]
    return [target]


def _match_filter(f: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    prop = f.get("property")
    op = f.get("operator")
    target = f.get("value")
    actual = context.get(prop) if prop is not None else None

    if op == "equals":
        return _coerced_equals(actual, target)
    if op == "not_equals":
        return not _coerced_equals(actual, target)
    if op == "contains":
        if actual is None:
            return False
        if isinstance(actual, (list, tuple, set)):
            return any(_coerced_equals(item, target) for item in actual)
        return str(target) in str(actual)
    if op == "in":
        return any(_coerced_equals(actual, candidate) for candidate in _as_membership(target))
    # Unknown operator: fail closed.
    return False


def _normalize(config: Any) -> dict[str, Any]:
    """Best-effort normalization of a stored config (tolerant, never raises)."""
    if isinstance(config, bool):
        return {
            "enabled": config,
            "rollout_percentage": 100 if config else 0,
            "filters": [],
        }
    if not isinstance(config, Mapping):
        return {"enabled": False, "rollout_percentage": 0, "filters": []}

    enabled = bool(config.get("enabled", False))
    pct = config.get("rollout_percentage", 100 if enabled else 0)
    try:
        pct = int(pct)
    except (TypeError, ValueError):
        pct = 0
    pct = max(0, min(100, pct))

    filters_in = config.get("filters") or []
    filters = [f for f in filters_in if isinstance(f, Mapping)]
    return {"enabled": enabled, "rollout_percentage": pct, "filters": filters}


def _identity(context: Mapping[str, Any], bucket_by: str | None) -> str | None:
    keys = (bucket_by,) if bucket_by else DEFAULT_IDENTITY_KEYS
    for key in keys:
        if key and context.get(key) not in (None, ""):
            return str(context[key])
    return None


def _bucket(flag_key: str, identity: str) -> float:
    """Deterministic fraction in [0, 1) for this flag + identity."""
    digest = hashlib.sha1(f"{flag_key}:{identity}".encode()).hexdigest()
    return int(digest[:_BUCKET_HEX_LEN], 16) / _BUCKET_MAX


def evaluate(
    config: Any,
    context: Mapping[str, Any] | None = None,
    *,
    flag_key: str,
    bucket_by: str | None = None,
) -> Evaluation:
    """Evaluate ``config`` against ``context`` and return an :class:`Evaluation`.

    ``context`` is a JSON-like object of properties the filters are matched
    against (and from which the rollout identity is read). ``flag_key`` seeds
    the rollout hash so buckets differ per flag. ``bucket_by`` overrides which
    context property is used as the rollout identity.
    """
    context = context or {}
    cfg = _normalize(config)

    if not cfg["enabled"]:
        return Evaluation(False, "Flag is disabled in this environment.")

    for f in cfg["filters"]:
        if not _match_filter(f, context):
            prop = f.get("property")
            op = f.get("operator")
            return Evaluation(
                False, f"Targeting filter not matched: {prop} {op} {f.get('value')!r}."
            )

    pct = cfg["rollout_percentage"]
    if pct >= 100:
        return Evaluation(True, "Matches targeting; 100% rollout.")
    if pct <= 0:
        return Evaluation(False, "Matches targeting but rollout is 0%.")

    identity = _identity(context, bucket_by)
    if identity is None:
        expected = bucket_by or " / ".join(DEFAULT_IDENTITY_KEYS)
        return Evaluation(
            False,
            f"Partial rollout ({pct}%) requires an identity in the context "
            f"(expected one of: {expected}).",
        )

    bucket = _bucket(flag_key, identity) * 100
    if bucket < pct:
        return Evaluation(True, f"In rollout bucket ({bucket:.1f} < {pct}%).")
    return Evaluation(False, f"Outside rollout bucket ({bucket:.1f} >= {pct}%).")


def is_enabled(
    config: Any,
    context: Mapping[str, Any] | None = None,
    *,
    flag_key: str,
    bucket_by: str | None = None,
) -> bool:
    """Convenience wrapper returning just the boolean outcome."""
    return evaluate(config, context, flag_key=flag_key, bucket_by=bucket_by).enabled


class FeatureFlagClient:
    """A tiny client holding a snapshot of flag configs keyed by flag key.

    Load it from the console's API/DB (a ``{flag_key: config}`` mapping for one
    environment) and evaluate flags by key in your application code.
    """

    def __init__(
        self,
        configs: Mapping[str, Any] | None = None,
        *,
        bucket_by: str | None = None,
    ) -> None:
        self._configs: dict[str, Any] = dict(configs or {})
        self._bucket_by = bucket_by

    def set_flag(self, flag_key: str, config: Any) -> None:
        self._configs[flag_key] = config

    def evaluate(
        self, flag_key: str, context: Mapping[str, Any] | None = None
    ) -> Evaluation:
        if flag_key not in self._configs:
            return Evaluation(False, f"Unknown flag '{flag_key}'.")
        return evaluate(
            self._configs[flag_key],
            context,
            flag_key=flag_key,
            bucket_by=self._bucket_by,
        )

    def is_enabled(
        self, flag_key: str, context: Mapping[str, Any] | None = None
    ) -> bool:
        return self.evaluate(flag_key, context).enabled
