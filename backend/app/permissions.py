"""Centralized role-based access control.

Sensitive operations are keyed off named permissions rather than scattered role
checks. `require_permission` must be called server-side for every mutation;
hiding a button in the UI is never sufficient.
"""

from typing import Literal

from app.errors import AppError
from app.models.enums import UserRole
from app.models.user import User

Permission = Literal[
    "kyc:read",
    "kyc:review",
    "refund:read",
    "refund:create",
    "feature_flag:read",
    "feature_flag:write_nonprod",
    "feature_flag:write_prod",
    "audit:read",
]

ALL_PERMISSIONS: tuple[Permission, ...] = (
    "kyc:read",
    "kyc:review",
    "refund:read",
    "refund:create",
    "feature_flag:read",
    "feature_flag:write_nonprod",
    "feature_flag:write_prod",
    "audit:read",
)

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: set(ALL_PERMISSIONS),
    UserRole.OPS_REVIEWER: {
        "kyc:read",
        "kyc:review",
        "refund:read",
        "refund:create",
        "feature_flag:read",
        "feature_flag:write_nonprod",
        "audit:read",
    },
    UserRole.SUPPORT_AGENT: {
        "refund:read",
        "refund:create",
        "feature_flag:read",
    },
    UserRole.READ_ONLY: {
        "kyc:read",
        "refund:read",
        "feature_flag:read",
        "audit:read",
    },
}

# Per-role refund limits, in integer minor units (cents). None = no prototype limit.
REFUND_LIMIT_MINOR: dict[UserRole, int | None] = {
    UserRole.ADMIN: None,
    UserRole.OPS_REVIEWER: 200_000,  # $2,000
    UserRole.SUPPORT_AGENT: 25_000,  # $250
    UserRole.READ_ONLY: 0,
}


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, set())


def require_permission(user: User, permission: Permission) -> None:
    if not has_permission(user, permission):
        raise AppError(
            "FORBIDDEN",
            f"You do not have permission to perform this action ({permission}).",
            {"permission": permission, "role": user.role.value},
        )


def permissions_for(user: User) -> list[str]:
    return sorted(p for p in ROLE_PERMISSIONS.get(user.role, set()))


def refund_limit_for(user: User) -> int | None:
    return REFUND_LIMIT_MINOR.get(user.role, 0)
