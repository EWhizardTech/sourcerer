"""Google OAuth code flow + portal session endpoints.

The portal is a confidential OAuth client: the browser only ever sees the
Google consent screen and our gateway callback. The ID token is obtained
directly from Google's token endpoint over TLS, so we validate its claims
(aud/iss/exp) without re-fetching Google's signing certs.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.db.models import User
from app.deps import CurrentAdmin, CurrentUser, DbSession
from app.services.security import (
    SESSION_COOKIE,
    STATE_COOKIE,
    cookie_kwargs,
    create_session_token,
    create_state_token,
    is_admin_email,
    verify_state_token,
)
from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal/auth", tags=["auth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect the browser to Google's consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    state, state_cookie = create_state_token()
    params = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_CALLBACK_URL,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(f"{_GOOGLE_AUTH_URL}?{params}", status_code=302)
    response.set_cookie(STATE_COOKIE, state_cookie, max_age=600, **cookie_kwargs())
    return response


@router.get("/callback")
async def callback(request: Request, db: DbSession) -> RedirectResponse:
    """Exchange the auth code, upsert the user, set the session cookie."""
    error_redirect = RedirectResponse(
        f"{settings.PORTAL_FRONTEND_ORIGIN}/signin?error=oauth", status_code=302
    )
    error_redirect.delete_cookie(STATE_COOKIE, path="/")

    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    state_cookie = request.cookies.get(STATE_COOKIE, "")
    if not code or not verify_state_token(state_cookie, state):
        logger.warning("OAuth callback rejected: missing code or bad state")
        return error_redirect

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_CALLBACK_URL,
                "grant_type": "authorization_code",
            },
        )
    if token_resp.status_code != 200:
        logger.error("Token exchange failed: %s", token_resp.text[:300])
        return error_redirect

    id_token = token_resp.json().get("id_token", "")
    # Signature already vouched for by the direct TLS exchange; check claims.
    claims = jwt.decode(
        id_token,
        options={"verify_signature": False, "verify_exp": True},
        audience=settings.GOOGLE_CLIENT_ID,
        algorithms=["RS256"],
    )
    if claims.get("iss") not in _GOOGLE_ISSUERS or not claims.get("sub"):
        logger.error("ID token claim check failed (iss=%s)", claims.get("iss"))
        return error_redirect

    email = (claims.get("email") or "").lower()
    if not email:
        return error_redirect

    now = datetime.now(timezone.utc)
    user = (
        await db.execute(select(User).where(User.google_sub == claims["sub"]))
    ).scalar_one_or_none()
    if user is None:
        user = User(google_sub=claims["sub"], email=email, created_at=now)
        db.add(user)
    user.email = email
    user.name = claims.get("name")
    user.picture_url = claims.get("picture")
    user.last_login_at = now
    await db.commit()

    response = RedirectResponse(
        f"{settings.PORTAL_FRONTEND_ORIGIN}/home", status_code=302
    )
    response.delete_cookie(STATE_COOKIE, path="/")
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(claims["sub"], email, user.name),
        max_age=settings.PORTAL_SESSION_TTL_SECONDS,
        **cookie_kwargs(),
    )
    return response


@router.get("/me")
async def me(user: CurrentUser) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture_url,
        "is_admin": is_admin_email(user.email),
    }


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/verify-admin", status_code=204)
async def verify_admin(_: CurrentAdmin) -> None:
    """Used by the gateway (future) to gate admin-only upstream routes."""
    return None
