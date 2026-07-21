"""Development authentication via a signed, HTTP-only session cookie.

This is intentionally lightweight (no passwords) so a reviewer can switch roles.
The cookie only stores a signed user id; all authorization still happens
server-side. Replacing this with Clerk / Auth0 / Okta / SSO later only requires
swapping how `current_user` is resolved.
"""

from itsdangerous import BadSignature, URLSafeSerializer

from app.config import settings

SESSION_COOKIE = "ioc_session"
_serializer = URLSafeSerializer(settings.session_secret, salt="ioc-session")


def sign_user_id(user_id: str) -> str:
    return _serializer.dumps({"user_id": user_id})


def unsign_user_id(token: str) -> str | None:
    try:
        data = _serializer.loads(token)
    except BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    user_id = data.get("user_id")
    return user_id if isinstance(user_id, str) else None
