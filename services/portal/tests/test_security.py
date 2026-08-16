"""Session/state token and admin-email helpers."""

from app.services.security import (
    create_content_ticket,
    create_session_token,
    create_state_token,
    decode_session_token,
    is_admin_email,
    verify_content_ticket,
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


def test_content_ticket_binds_file_and_user():
    tok = create_content_ticket("file1", "sub1", 300)
    assert verify_content_ticket(tok, "file1", "sub1")
    assert not verify_content_ticket(tok, "file2", "sub1")  # wrong file
    assert not verify_content_ticket(tok, "file1", "sub2")  # wrong user
    assert not verify_content_ticket("garbage", "file1", "sub1")


def test_content_ticket_expires():
    expired = create_content_ticket("file1", "sub1", -1)  # already past
    assert not verify_content_ticket(expired, "file1", "sub1")


def test_session_token_not_valid_as_content_ticket():
    # A session token has no content audience -> can't be reused as a ticket.
    sess = create_session_token("sub1", "a@b.com", "A")
    assert not verify_content_ticket(sess, "file1", "sub1")


def test_admin_emails(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "Owner@Gmail.com, second@x.com")
    assert is_admin_email("owner@gmail.com")
    assert is_admin_email("SECOND@X.COM")
    assert not is_admin_email("intruder@x.com")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "")
    assert not is_admin_email("owner@gmail.com")
