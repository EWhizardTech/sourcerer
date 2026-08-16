"""Session and OAuth-state token helpers (HS256 JWTs via PyJWT)."""

import time
import uuid

import jwt

from sourcerer_core.config import settings

SESSION_COOKIE = "sourcerer_session"
STATE_COOKIE = "sourcerer_oauth_state"
_ALGO = "HS256"
_STATE_TTL_SECONDS = 600


def create_session_token(user_id: str, email: str, name: str | None) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "name": name,
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
