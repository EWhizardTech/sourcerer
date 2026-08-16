"""Shared FastAPI dependencies: DB session, current user, admin gate."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.services.security import SESSION_COOKIE, decode_session_token, is_admin_email

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def current_user(request: Request, db: DbSession) -> User:
    """Resolve the session cookie to a live User row or raise 401."""
    token = request.cookies.get(SESSION_COOKIE)
    claims = decode_session_token(token) if token else None
    if not claims:
        raise HTTPException(status_code=401, detail="Not signed in")
    user = (
        await db.execute(select(User).where(User.google_sub == claims["sub"]))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    # Reject sessions minted before the last logout / admin revoke.
    if claims.get("sv") != user.session_version:
        raise HTTPException(status_code=401, detail="Session revoked")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def current_admin(user: CurrentUser) -> User:
    if not is_admin_email(user.email):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


CurrentAdmin = Annotated[User, Depends(current_admin)]
