"""Direct-access guard on content endpoints (Sec-Fetch + client header)."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.content import _guard_content_request


def _req(headers: dict) -> SimpleNamespace:
    # Starlette lowercases header names in the ASGI scope; mimic that.
    return SimpleNamespace(headers={k.lower(): v for k, v in headers.items()})


def test_spa_fetch_is_allowed():
    _guard_content_request(
        _req(
            {
                "X-Sourcerer-Client": "1",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Site": "same-origin",
            }
        )
    )  # no raise


def test_same_origin_media_element_is_allowed():
    # <video>/<img> can't send a custom header; allowed via Sec-Fetch.
    _guard_content_request(
        _req(
            {
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Dest": "video",
                "Sec-Fetch-Site": "same-site",
            }
        )
    )  # no raise


def test_open_in_new_tab_is_blocked():
    with pytest.raises(HTTPException) as exc:
        _guard_content_request(
            _req(
                {
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Site": "same-origin",
                }
            )
        )
    assert exc.value.status_code == 403


def test_bare_curl_is_blocked():
    # No Sec-Fetch headers, no client header.
    with pytest.raises(HTTPException) as exc:
        _guard_content_request(_req({}))
    assert exc.value.status_code == 403


def test_cross_site_media_is_blocked():
    with pytest.raises(HTTPException) as exc:
        _guard_content_request(
            _req(
                {
                    "Sec-Fetch-Mode": "no-cors",
                    "Sec-Fetch-Dest": "video",
                    "Sec-Fetch-Site": "cross-site",
                }
            )
        )
    assert exc.value.status_code == 403
