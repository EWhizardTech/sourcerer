"""Server-side session revocation via users.session_version."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps import current_user
from app.services.security import SESSION_COOKIE, create_session_token
from tests.conftest import make_user


def _request(token: str) -> SimpleNamespace:
    # current_user only touches request.cookies.get(...).
    return SimpleNamespace(cookies={SESSION_COOKIE: token})


@pytest.mark.asyncio
async def test_current_token_is_accepted(db):
    user = make_user()
    db.add(user)
    await db.commit()
    token = create_session_token(
        user.google_sub, user.email, user.name, user.session_version
    )
    resolved = await current_user(_request(token), db)
    assert resolved.id == user.id


@pytest.mark.asyncio
async def test_bumped_session_version_revokes_old_token(db):
    user = make_user()
    db.add(user)
    await db.commit()
    token = create_session_token(
        user.google_sub, user.email, user.name, user.session_version
    )
    # Simulate logout / admin revoke.
    user.session_version += 1
    await db.commit()
    with pytest.raises(HTTPException) as exc:
        await current_user(_request(token), db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_token_without_version_claim_is_rejected(db):
    """A legacy token minted before this change carries no sv claim."""
    user = make_user()
    db.add(user)
    await db.commit()
    import jwt

    from sourcerer_core.config import settings

    legacy = jwt.encode(
        {"sub": user.google_sub, "email": user.email, "exp": 9999999999},
        settings.PORTAL_SESSION_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        await current_user(_request(legacy), db)
    assert exc.value.status_code == 401
