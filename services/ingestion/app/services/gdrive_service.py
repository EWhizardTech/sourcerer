"""Google Drive ingestion service.

Responsibilities:
  - Authenticate with Google Drive via service account.
  - Recursively list files in a folder and all its subfolders.
  - Download file content into memory (bytes).
  - Return a list of FileRecord dicts with stable file_id across runs.

Supported MIME types (Stage 1 — no parsing yet):
  - PDF
  - Plain text / Markdown
  - DOCX (Google export from Docs, or uploaded .docx)
  - PPT / PPTX
"""

import io
import logging
from typing import TypedDict

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

# Read-only Drive scope is sufficient for listing + downloading.
_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Map of supported MIME types → human-readable label.
# file_id is Google's stable identifier, unchanged across renames/moves.
SUPPORTED_MIME_TYPES: set[str] = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    # DOCX uploaded directly or exported from Google Docs.
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # PPT uploaded directly.
    "application/vnd.ms-powerpoint",
    # PPTX uploaded directly or exported from Google Slides.
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Google Docs/Slides/Sheets — exportable to docx/pptx/pdf.
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.presentation",
}

# Export targets for Google Workspace MIME types.
# We export Google Docs → DOCX, Slides → PPTX for downstream parsing.
_GOOGLE_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
}


class FileRecord(TypedDict):
    """Structured record for a single ingested file."""

    file_id: str  # Stable Google Drive fileId.
    file_name: str  # Original file name.
    mime_type: str  # MIME type (after export if applicable).
    file_path: str  # Full breadcrumb path: "Folder / Sub / file.pdf".
    modified_time: str  # ISO8601 last-modified timestamp.
    content: bytes  # Raw file bytes (in-memory download).


def build_drive_client():
    """Build and return an authenticated Google Drive API client.

    Uses a service account JSON key at the path configured in settings.
    """
    credentials = service_account.Credentials.from_service_account_file(
        settings.GDRIVE_SERVICE_ACCOUNT_PATH,
        scopes=_SCOPES,
    )
    # cache_discovery=False avoids stale discovery doc issues in prod.
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _get_folder_path(service, folder_id: str) -> str:
    """Walk the parent chain of folder_id to build a '/' separated path.

    Stops walking when reaching 'My Drive' root or when a parent can't be
    retrieved (e.g. Shared Drive root).

    Args:
        service: Authenticated Drive API client.
        folder_id: ID of the folder whose path to resolve.

    Returns:
        Human-readable path string, e.g. "Root / Research / Papers".
    """
    path_parts: list[str] = []
    current_id = folder_id

    # Walk upward through parent folders (max 20 hops to avoid infinite loops).
    for _ in range(20):
        try:
            meta = (
                service.files()
                .get(
                    fileId=current_id,
                    fields="id, name, parents",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Could not fetch parent folder %s: %s", current_id, exc)
            break

        path_parts.insert(0, meta["name"])

        parents = meta.get("parents")
        if not parents:
            # Reached the drive root.
            break
        current_id = parents[0]

    return " / ".join(path_parts) if path_parts else folder_id


def _download_file(service, file_id: str) -> bytes:
    """Download a regular Drive file into memory as bytes.

    Args:
        service: Authenticated Drive API client.
        file_id: Google Drive file ID.

    Returns:
        Raw file content as bytes.
    """
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()


def _export_google_file(service, file_id: str, export_mime: str) -> bytes:
    """Export a Google Workspace file (Docs/Slides) to a standard MIME type.

    Args:
        service: Authenticated Drive API client.
        file_id: Google Drive file ID.
        export_mime: Target MIME type for export (e.g., DOCX, PPTX).

    Returns:
        Exported file content as bytes.
    """
    request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()


# MIME type for Google Drive folders — used when finding subfolders.
_FOLDER_MIME = "application/vnd.google-apps.folder"

# Precomputed query fragment for supported file MIME filters (built once).
_MIME_CONDITIONS = " or ".join(f"mimeType='{m}'" for m in SUPPORTED_MIME_TYPES)


def _collect_files_recursive(
    service,
    folder_id: str,
    folder_path: str,
    records: list[FileRecord],
    visited: set[str],
) -> None:
    """Recursively collect supported files from a Drive folder into `records`.

    Visits all subfolders depth-first, avoiding cycles via a `visited` set.
    Files that fail to download are skipped (error logged) so a single bad
    file never aborts the whole traversal.

    Args:
        service: Authenticated Drive API client.
        folder_id: Current folder to process.
        folder_path: Human-readable breadcrumb path for the current folder.
        records: Accumulator list — mutated in place.
        visited: Set of already-visited folder IDs to guard against cycles.
    """
    if folder_id in visited:
        logger.warning(
            "Cycle detected — skipping already-visited folder: %s", folder_id
        )
        return
    visited.add(folder_id)

    logger.info("Scanning folder: %s (id=%s)", folder_path, folder_id)

    # ---- 1. Process all supported files in this folder --------------------
    file_query = (
        f"'{folder_id}' in parents" f" and ({_MIME_CONDITIONS})" f" and trashed=false"
    )
    page_token: str | None = None

    while True:
        response = (
            service.files()
            .list(
                q=file_query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        for item in response.get("files", []):
            file_id: str = item["id"]
            file_name: str = item["name"]
            mime_type: str = item["mimeType"]
            modified_time: str = item.get("modifiedTime", "")

            logger.info("Downloading: %s (%s)", file_name, mime_type)

            try:
                if mime_type in _GOOGLE_EXPORT_MAP:
                    # Google Workspace file — export to binary format.
                    export_mime, ext = _GOOGLE_EXPORT_MAP[mime_type]
                    content = _export_google_file(service, file_id, export_mime)
                    mime_type = export_mime
                    if not file_name.endswith(ext):
                        file_name = file_name + ext
                else:
                    content = _download_file(service, file_id)

            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to download %s: %s", file_name, exc)
                continue  # Skip failed file; continue with the rest.

            records.append(
                FileRecord(
                    file_id=file_id,
                    file_name=file_name,
                    mime_type=mime_type,
                    file_path=f"{folder_path} / {file_name}",
                    modified_time=modified_time,
                    content=content,
                )
            )
            logger.info("Ingested: %s (%d bytes)", file_name, len(content))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    # ---- 2. Recurse into subfolders ----------------------------------------
    subfolder_query = (
        f"'{folder_id}' in parents"
        f" and mimeType='{_FOLDER_MIME}'"
        f" and trashed=false"
    )
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=subfolder_query,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        for subfolder in response.get("files", []):
            sub_id: str = subfolder["id"]
            sub_name: str = subfolder["name"]
            sub_path = f"{folder_path} / {sub_name}"
            _collect_files_recursive(service, sub_id, sub_path, records, visited)

        page_token = response.get("nextPageToken")
        if not page_token:
            break


def list_files_in_folder(folder_id: str) -> list[FileRecord]:
    """List and download all supported files in a Google Drive folder.

    Recursively traverses all subfolders. Filters by SUPPORTED_MIME_TYPES.
    Downloads each file content into memory.

    Args:
        folder_id: Google Drive folder ID to ingest from.

    Returns:
        List of FileRecord dicts, one per successfully ingested file.

    Raises:
        googleapiclient.errors.HttpError: On Drive API failure.
    """
    service = build_drive_client()

    # Resolve human-readable root path (used as breadcrumb prefix).
    root_path = _get_folder_path(service, folder_id)
    logger.info("Starting recursive ingestion from: %s (id=%s)", root_path, folder_id)

    records: list[FileRecord] = []
    _collect_files_recursive(
        service=service,
        folder_id=folder_id,
        folder_path=root_path,
        records=records,
        visited=set(),  # Track visited folders to guard against symlink-like cycles.
    )

    logger.info("Total files ingested: %d", len(records))
    return records
