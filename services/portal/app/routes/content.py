"""Access-checked content endpoints. Drive URLs never leave this service.

/raw streams bytes straight from the Drive API (Range-aware, so mp4 seeking
works through the double proxy); /pdf serves the converted document. Every
successful content hit writes an audit row.
"""

import asyncio
import logging
import re
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

import httpx

from app.db.models import DriveNode
from app.deps import CurrentUser, DbSession
from app.services import audit
from app.services.access import user_can_access
from app.services.converter import GOOGLE_EXPORT_PDF, OFFICE_TO_PDF, get_pdf
from app.services.gdrive import get_access_token
from app.services.security import create_content_ticket, verify_content_ticket
from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal/content", tags=["content"])

_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
# Every content response: never cache, never MIME-sniff, and neutralize any
# active document (HTML/SVG) if it is ever rendered as a top-level navigation.
# The portal SPA fetches these bytes via fetch()/media elements, so `sandbox`
# and `default-src 'none'` don't affect normal viewing — they only bite when a
# file is opened directly, which is exactly the same-origin XSS vector we close.
_SECURE_HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox; frame-ancestors 'none'",
}
# MIME types the browser would execute script from if rendered inline; force a
# download disposition for these so a direct link can't run in our origin.
_ACTIVE_MIMES = {
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
    "application/xml",
    "text/xml",
    "text/xsl",
}

_TEXT_EXTENSIONS = {
    "txt", "sql", "md", "py", "c", "cpp", "h", "hpp", "js", "ts", "java",
    "html", "css", "json", "yaml", "yml", "ini", "sh", "asm", "m", "csv",
    "php", "r", "ipynb",
}

# Cached service-account bearer token (valid ~1h, refresh at 50min).
_token_cache: dict = {"token": None, "acquired": 0.0}
_token_lock = asyncio.Lock()


def _content_disposition(filename: str, mime_type: str = "") -> str:
    """Build a Content-Disposition that survives Starlette's latin-1 header
    encoding. Non-latin-1 names (CJK, em dashes, curly quotes) would otherwise
    raise UnicodeEncodeError and 500 the view. Per RFC 6266/5987 we emit an
    ASCII fallback plus a UTF-8 filename*. Active document types are forced to
    `attachment` so a direct link can't render script in our origin."""
    disposition = "attachment" if mime_type in _ACTIVE_MIMES else "inline"
    fallback = (
        re.sub(r'[\r\n"\\]', "_", filename).encode("ascii", "replace").decode("ascii")
    )
    return (
        f"{disposition}; filename=\"{fallback}\"; "
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


async def _drive_token() -> str:
    async with _token_lock:
        if _token_cache["token"] and time.monotonic() - _token_cache["acquired"] < 3000:
            return _token_cache["token"]
        token = await asyncio.to_thread(get_access_token)
        _token_cache.update(token=token, acquired=time.monotonic())
        return token


def classify_viewer(node: DriveNode) -> str:
    mime = node.mime_type
    ext = node.name.rsplit(".", 1)[-1].lower() if "." in node.name else ""
    if mime == "application/pdf":
        return "pdf"
    if mime in GOOGLE_EXPORT_PDF:
        return "gdoc-pdf"
    if mime in OFFICE_TO_PDF:
        return "office-pdf"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/") or mime.startswith("audio/"):
        return "video"
    if mime == "text/markdown" or ext == "md":
        return "md"
    if mime.startswith("text/") or ext in _TEXT_EXTENSIONS:
        return "text"
    return "unsupported"


def _guard_content_request(request: Request) -> None:
    """Allow content bytes only for in-app requests, not direct URL access.

    Sec-Fetch-* are browser-set and cannot be forged by page script, so they
    reliably distinguish an in-app fetch()/media load from a top-level
    navigation (open-in-new-tab / address bar). We additionally require the
    SPA's custom header, which curl and navigations don't send. This blocks the
    'copy the /raw URL from DevTools and open/share it' vector and casual curl.
    It cannot stop a user who replays the app's exact request (their own cookie
    + header) — that byte access is inherent to being granted the file.
    """
    h = request.headers
    # 1) Never serve a top-level navigation.
    if h.get("sec-fetch-mode") == "navigate" or h.get("sec-fetch-dest") == "document":
        raise HTTPException(status_code=403, detail="Open Sourcerer to view this file")
    # 2) SPA fetch() carries our header; a <video>/<img> element can't add
    #    headers, so allow same-origin/-site media loads by Sec-Fetch instead.
    if h.get("x-sourcerer-client") == "1":
        return
    if h.get("sec-fetch-site") in {"same-origin", "same-site"} and h.get(
        "sec-fetch-dest"
    ) in {"video", "audio", "image"}:
        return
    raise HTTPException(status_code=403, detail="Direct content access not allowed")


async def _accessible_node(
    file_id: str, user: CurrentUser, db: DbSession
) -> DriveNode:
    node = (
        await db.execute(select(DriveNode).where(DriveNode.id == file_id))
    ).scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="Not found")
    if node.is_folder:
        raise HTTPException(status_code=400, detail="Not a file")
    if not await user_can_access(db, user, node):
        raise HTTPException(status_code=403, detail="No active access grant")
    return node


@router.get("/{file_id}/meta")
async def meta(
    file_id: str, request: Request, user: CurrentUser, db: DbSession
) -> dict:
    _guard_content_request(request)
    node = await _accessible_node(file_id, user, db)
    viewer = classify_viewer(node)
    # A short-lived signed ticket bound to this file + this user. Streamed media
    # gets a longer window (one <video> URL must survive the whole playback).
    ttl = (
        settings.PORTAL_CONTENT_STREAM_TTL_SECONDS
        if viewer == "video"
        else settings.PORTAL_CONTENT_TICKET_TTL_SECONDS
    )
    return {
        "id": node.id,
        "name": node.name,
        "mime_type": node.mime_type,
        "size": node.size,
        "path": node.path_names,
        "modified_time": (
            node.modified_time.isoformat() if node.modified_time else None
        ),
        "viewer": viewer,
        "ticket": create_content_ticket(node.id, user.google_sub, ttl),
    }


@router.get("/{file_id}/raw")
async def raw(
    file_id: str, request: Request, user: CurrentUser, db: DbSession
) -> StreamingResponse:
    _guard_content_request(request)
    node = await _accessible_node(file_id, user, db)
    if not verify_content_ticket(
        request.query_params.get("t", ""), node.id, user.google_sub
    ):
        raise HTTPException(status_code=403, detail="Invalid or expired content link")
    if node.mime_type in GOOGLE_EXPORT_PDF:
        raise HTTPException(status_code=409, detail="Use the /pdf endpoint")

    token = await _drive_token()
    # identity: Drive otherwise gzips (aiter_raw would forward compressed
    # bytes), and Range offsets must refer to the real file bytes.
    upstream_headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Encoding": "identity",
    }
    if range_header := request.headers.get("range"):
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, read=None)  # no read timeout: large streams
    )
    upstream = client.build_request(
        "GET",
        f"{_DRIVE_FILES_URL}/{node.id}",
        params={"alt": "media", "supportsAllDrives": "true"},
        headers=upstream_headers,
    )
    response = await client.send(upstream, stream=True)
    if response.status_code >= 400:
        await response.aclose()
        await client.aclose()
        logger.error("Drive media fetch failed (%s) for %s", response.status_code, node.id)
        raise HTTPException(status_code=502, detail="Upstream fetch failed")

    await audit.record(
        db, "content_viewed", user_id=user.id, node_id=node.id, meta={"kind": "raw"}
    )
    await db.commit()

    passthrough = {
        k: v
        for k, v in response.headers.items()
        if k.lower() in {"content-length", "content-range", "accept-ranges"}
    }

    async def stream_and_close():
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_and_close(),
        status_code=response.status_code,
        media_type=node.mime_type,
        headers={
            **passthrough,
            **_SECURE_HEADERS,
            "Content-Disposition": _content_disposition(node.name, node.mime_type),
        },
    )


@router.get("/{file_id}/pdf")
async def converted_pdf(
    file_id: str, request: Request, user: CurrentUser, db: DbSession
) -> FileResponse:
    _guard_content_request(request)
    node = await _accessible_node(file_id, user, db)
    if not verify_content_ticket(
        request.query_params.get("t", ""), node.id, user.google_sub
    ):
        raise HTTPException(status_code=403, detail="Invalid or expired content link")
    if node.mime_type not in GOOGLE_EXPORT_PDF | OFFICE_TO_PDF:
        raise HTTPException(status_code=409, detail="Use the /raw endpoint")
    try:
        pdf_path: Path = await get_pdf(node)
    except RuntimeError as exc:
        logger.error("Conversion failed for %s: %s", node.id, exc)
        raise HTTPException(status_code=502, detail="Conversion failed") from exc

    await audit.record(
        db, "content_viewed", user_id=user.id, node_id=node.id, meta={"kind": "pdf"}
    )
    await db.commit()
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={
            **_SECURE_HEADERS,
            "Content-Disposition": _content_disposition(
                f"{Path(node.name).stem}.pdf", "application/pdf"
            ),
        },
    )
