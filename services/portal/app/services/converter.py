"""Office/Google-native -> PDF conversion with a content-addressed disk cache.

- Google Docs/Slides/Sheets: Drive `files.export` to PDF (built-in, free).
- pptx/ppt/docx/doc: headless LibreOffice (`soffice`) in this container.

Cache layout: {PORTAL_CACHE_DIR}/{file_id}/{version_key}.pdf where
version_key = md5Checksum (uploads) or sha1(modifiedTime) (Google-native).
Writing a new version prunes the file's older cached PDFs. Conversions are
synchronous-in-request, deduped by a per-file lock and bounded by a global
semaphore — right-sized for a small cohort; swappable for a queue later.
"""

import asyncio
import hashlib
import io
import logging
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

from googleapiclient.http import MediaIoBaseDownload

from app.db.models import DriveNode
from app.services.gdrive import build_drive_client, download_file_bytes
from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_EXPORT_PDF = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.spreadsheet",
}
OFFICE_TO_PDF = {
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_file_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_convert_slots = asyncio.Semaphore(2)


def version_key(node: DriveNode) -> str:
    if node.md5_checksum:
        return node.md5_checksum
    stamp = node.modified_time.isoformat() if node.modified_time else "unknown"
    return hashlib.sha1(stamp.encode()).hexdigest()


def cached_pdf_path(node: DriveNode) -> Path:
    return Path(settings.PORTAL_CACHE_DIR) / node.id / f"{version_key(node)}.pdf"


def _export_pdf_bytes(file_id: str) -> bytes:
    """Blocking Drive export of a Google-native file to PDF (via to_thread)."""
    service = build_drive_client()
    request = service.files().export_media(
        fileId=file_id, mimeType="application/pdf"
    )
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


async def _soffice_convert(src_path: Path, out_dir: Path) -> Path:
    process = await asyncio.create_subprocess_exec(
        "soffice",
        "--headless",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out_dir),
        str(src_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(), timeout=settings.PORTAL_CONVERT_TIMEOUT_SECONDS
        )
    except TimeoutError:
        process.kill()
        raise RuntimeError("LibreOffice conversion timed out")
    produced = out_dir / f"{src_path.stem}.pdf"
    if process.returncode != 0 or not produced.exists():
        raise RuntimeError(
            f"LibreOffice failed (rc={process.returncode}): {stderr.decode()[:300]}"
        )
    return produced


def _finalize_cache(node: DriveNode, pdf_bytes_or_path: bytes | Path) -> Path:
    """Atomically install the new PDF and prune stale versions."""
    target = cached_pdf_path(node)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    if isinstance(pdf_bytes_or_path, bytes):
        tmp.write_bytes(pdf_bytes_or_path)
    else:
        shutil.move(str(pdf_bytes_or_path), tmp)
    tmp.replace(target)
    for stale in target.parent.glob("*.pdf"):
        if stale != target:
            stale.unlink(missing_ok=True)
    return target


async def get_pdf(node: DriveNode) -> Path:
    """Return a cached-or-freshly-converted PDF for an office/gdoc node."""
    cached = cached_pdf_path(node)
    if cached.exists():
        return cached

    async with _file_locks[node.id]:
        if cached.exists():  # converted while we waited on the lock
            return cached
        async with _convert_slots:
            if node.mime_type in GOOGLE_EXPORT_PDF:
                pdf_bytes = await asyncio.to_thread(_export_pdf_bytes, node.id)
                return _finalize_cache(node, pdf_bytes)
            if node.mime_type in OFFICE_TO_PDF:
                raw = await asyncio.to_thread(download_file_bytes, node.id)
                suffix = Path(node.name).suffix or ".bin"
                with tempfile.TemporaryDirectory() as tmpdir:
                    src = Path(tmpdir) / f"source{suffix}"
                    src.write_bytes(raw)
                    produced = await _soffice_convert(src, Path(tmpdir))
                    return _finalize_cache(node, produced)
    raise RuntimeError(f"No PDF conversion for mime type {node.mime_type}")
