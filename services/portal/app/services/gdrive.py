"""Portal Drive client — METADATA ONLY during sync, bytes only on demand.

Adapted from services/ingestion gdrive_service, but fundamentally different:
the catalog walk never downloads content (no cloud cost), and on-demand
content access streams straight from the Drive API to the viewer. Uses the
same read-only service account.
"""

import fnmatch
import io
import logging
from collections import deque
from typing import TypedDict

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"

_LIST_FIELDS = (
    "nextPageToken, "
    "files(id, name, mimeType, size, modifiedTime, md5Checksum, parents)"
)


class NodeRecord(TypedDict):
    id: str
    parent_id: str | None
    name: str
    mime_type: str
    is_folder: bool
    size: int | None
    modified_time: str | None  # ISO8601 from the API
    md5_checksum: str | None
    path_ids: str  # "/rootId/.../selfId/"
    path_names: str  # "Academic_Resources/Sub/name"
    depth: int


def build_drive_client():
    credentials = service_account.Credentials.from_service_account_file(
        settings.GDRIVE_SERVICE_ACCOUNT_PATH, scopes=_SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def get_access_token() -> str:
    """Fresh OAuth2 bearer token for raw (streaming/Range) Drive HTTP calls."""
    credentials = service_account.Credentials.from_service_account_file(
        settings.GDRIVE_SERVICE_ACCOUNT_PATH, scopes=_SCOPES
    )
    credentials.refresh(GoogleAuthRequest())
    return credentials.token


def download_file_bytes(file_id: str, service=None) -> bytes:
    """Blocking full download of one file (call via asyncio.to_thread)."""
    service = service or build_drive_client()
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def _exclude_patterns() -> list[str]:
    return [p.strip() for p in settings.PORTAL_SYNC_EXCLUDE.split(",") if p.strip()]


def _is_excluded(name: str, patterns: list[str]) -> bool:
    if name.startswith("."):
        return True  # dotfiles/dirs — .obsidian etc.
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, p.lower()) for p in patterns)


def walk_folder_metadata(root_folder_id: str) -> list[NodeRecord]:
    """BFS the folder tree, returning metadata records for every kept node.

    One `files.list` per folder (pageSize 1000). OR-ing multiple `in parents`
    clauses looks attractive but the Drive API silently returns EMPTY result
    sets for 3+ OR'd parents (verified empirically) — never batch parents.
    Blocking function — call via asyncio.to_thread.
    """
    service = build_drive_client()
    patterns = _exclude_patterns()

    root = (
        service.files()
        .get(fileId=root_folder_id, fields="id, name, mimeType", supportsAllDrives=True)
        .execute()
    )
    records: list[NodeRecord] = [
        NodeRecord(
            id=root["id"],
            parent_id=None,
            name=root["name"],
            mime_type=root["mimeType"],
            is_folder=True,
            size=None,
            modified_time=None,
            md5_checksum=None,
            path_ids=f"/{root['id']}/",
            path_names=root["name"],
            depth=0,
        )
    ]

    # folder_id -> its NodeRecord (for path/depth of children)
    known_folders = {root["id"]: records[0]}
    queue: deque[str] = deque([root["id"]])
    visited: set[str] = set()
    seen_ids: set[str] = {root["id"]}  # legacy multi-parent files dedupe

    while queue:
        folder_id = queue.popleft()
        if folder_id in visited:
            continue
        visited.add(folder_id)
        if len(visited) % 200 == 0:
            logger.info(
                "Catalog walk progress: %d folders scanned, %d nodes, %d queued",
                len(visited), len(records), len(queue),
            )

        query = f"'{folder_id}' in parents and trashed=false"
        page_token: str | None = None

        while True:
            response = (
                service.files()
                .list(
                    q=query,
                    fields=_LIST_FIELDS,
                    pageSize=1000,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            for item in response.get("files", []):
                parent_id = next(
                    (p for p in item.get("parents", []) if p in known_folders), None
                )
                if parent_id is None or item["id"] in seen_ids:
                    continue  # parent outside the walked tree, or already seen
                if _is_excluded(item["name"], patterns):
                    continue  # excluded folder: never enqueued -> subtree pruned
                seen_ids.add(item["id"])
                parent = known_folders[parent_id]
                is_folder = item["mimeType"] == FOLDER_MIME
                record = NodeRecord(
                    id=item["id"],
                    parent_id=parent_id,
                    name=item["name"],
                    mime_type=item["mimeType"],
                    is_folder=is_folder,
                    size=int(item["size"]) if item.get("size") else None,
                    modified_time=item.get("modifiedTime"),
                    md5_checksum=item.get("md5Checksum"),
                    path_ids=f"{parent['path_ids']}{item['id']}/",
                    path_names=f"{parent['path_names']}/{item['name']}",
                    depth=parent["depth"] + 1,
                )
                records.append(record)
                if is_folder:
                    known_folders[item["id"]] = record
                    queue.append(item["id"])

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    logger.info("Catalog walk finished: %d nodes kept", len(records))
    return records
