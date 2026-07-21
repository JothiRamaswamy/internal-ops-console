from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models.user import User
from app.permissions import permissions_for, refund_limit_for
from app.schemas import LoginRequest
from app.security import SESSION_COOKIE, sign_user_id
from app.serializers import user_summary

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _me_payload(user: User) -> dict:
    payload = user_summary(user) or {}
    payload["permissions"] = permissions_for(user)
    payload["refund_limit_minor"] = refund_limit_for(user)
    return payload


@router.get("/users")
def list_users(db: Session = Depends(get_db)) -> list[dict]:
    """Dev-only helper powering the user/role switcher."""
    users = db.execute(select(User).order_by(User.role)).scalars().all()
    return [user_summary(u) for u in users]


@router.post("/login")
def login(
    body: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> dict:
    user: User | None = None
    if body.user_id:
        user = db.get(User, body.user_id)
    elif body.email:
        user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        raise AppError("NOT_FOUND", "No matching user to sign in as.")

    response.set_cookie(
        key=SESSION_COOKIE,
        value=sign_user_id(user.id),
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=60 * 60 * 24 * 7,
    )
    return _me_payload(user)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return _me_payload(user)
