from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models.user import User
from app.security import SESSION_COOKIE, unsign_user_id


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AppError("UNAUTHENTICATED", "No active session. Please sign in.")
    user_id = unsign_user_id(token)
    if not user_id:
        raise AppError("UNAUTHENTICATED", "Invalid session. Please sign in again.")
    user = db.get(User, user_id)
    if not user:
        raise AppError("UNAUTHENTICATED", "Session user not found.")
    return user


def client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None
