"""Session/state token and admin-email helpers."""

from app.services.security import (
    create_session_token,
    create_state_token,
    decode_session_token,
    is_admin_email,
    verify_state_token,
)
from sourcerer_core.config import settings


def test_session_token_round_trip():
    token = create_session_token("sub123", "a@b.com", "A")
    claims = decode_session_token(token)
    assert claims and claims["sub"] == "sub123" and claims["email"] == "a@b.com"


def test_tampered_token_rejected():
    token = create_session_token("sub123", "a@b.com", "A")
    assert decode_session_token(token[:-2] + "xx") is None
    assert decode_session_token("garbage") is None


def test_state_token_round_trip():
    state, cookie = create_state_token()
    assert verify_state_token(cookie, state)
    assert not verify_state_token(cookie, "other-state")
    assert not verify_state_token("garbage", state)


def test_admin_emails(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "Owner@Gmail.com, second@x.com")
    assert is_admin_email("owner@gmail.com")
    assert is_admin_email("SECOND@X.COM")
    assert not is_admin_email("intruder@x.com")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "")
    assert not is_admin_email("owner@gmail.com")
