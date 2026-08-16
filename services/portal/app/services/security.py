"""Session and OAuth-state token helpers (HS256 JWTs via PyJWT)."""

import time
import uuid

import jwt

from sourcerer_core.config import settings

SESSION_COOKIE = "sourcerer_session"
STATE_COOKIE = "sourcerer_oauth_state"
_ALGO = "HS256"
_STATE_TTL_SECONDS = 600


def create_session_token(
    user_id: str, email: str, name: str | None, session_version: int = 0
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "name": name,
            "sv": session_version,  # server-side revocation counter
            "iat": now,
            "exp": now + settings.PORTAL_SESSION_TTL_SECONDS,
        },
        settings.PORTAL_SESSION_SECRET,
        algorithm=_ALGO,
    )


def decode_session_token(token: str) -> dict | None:
    """Return claims for a valid session token, else None."""
    try:
        return jwt.decode(token, settings.PORTAL_SESSION_SECRET, algorithms=[_ALGO])
    except jwt.InvalidTokenError:
        return None


_CONTENT_AUD = "content"


def create_content_ticket(file_id: str, user_sub: str, ttl_seconds: int) -> str:
    """Short-lived token that authorizes streaming ONE file for ONE user. Bound
    into the content URL so a copied link expires quickly and is useless to a
    different user (checked against the session on top)."""
    now = int(time.time())
    return jwt.encode(
        {
            "fid": file_id,
            "sub": user_sub,
            "aud": _CONTENT_AUD,
            "iat": now,
            "exp": now + ttl_seconds,
        },
        settings.PORTAL_SESSION_SECRET,
        algorithm=_ALGO,
    )


def verify_content_ticket(token: str, file_id: str, user_sub: str) -> bool:
    try:
        claims = jwt.decode(
            token,
            settings.PORTAL_SESSION_SECRET,
            algorithms=[_ALGO],
            audience=_CONTENT_AUD,
        )
    except jwt.InvalidTokenError:
        return False
    return claims.get("fid") == file_id and claims.get("sub") == user_sub


def create_state_token() -> tuple[str, str]:
    """Return (state, signed short-lived cookie value) for the OAuth flow."""
    state = uuid.uuid4().hex
    now = int(time.time())
    token = jwt.encode(
        {"state": state, "iat": now, "exp": now + _STATE_TTL_SECONDS},
        settings.PORTAL_SESSION_SECRET,
        algorithm=_ALGO,
    )
    return state, token


def verify_state_token(token: str, state: str) -> bool:
    claims = decode_session_token(token)
    return bool(claims) and claims.get("state") == state


def is_admin_email(email: str) -> bool:
    admins = {e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()}
    return email.lower() in admins


def cookie_kwargs() -> dict:
    """Shared Set-Cookie attributes driven by env (dev vs prod)."""
    return {
        "httponly": True,
        "secure": settings.PORTAL_COOKIE_SECURE,
        "samesite": settings.PORTAL_COOKIE_SAMESITE,
        "path": "/",
    }
