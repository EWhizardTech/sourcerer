"""Unit tests for gdrive_service.py.

Tests are isolated — the Google Drive API is fully mocked via unittest.mock,
so no network calls or credentials are required.

Run with:
    uv run pytest tests/ -v
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.services.gdrive_service import (SUPPORTED_MIME_TYPES,
                                         _collect_files_recursive,
                                         _get_folder_path,
                                         list_files_in_folder)

# ---------------------------------------------------------------------------
# _get_folder_path
# ---------------------------------------------------------------------------


def test_get_folder_path_single_level():
    """Should return just the folder name when there are no parents."""
    service = MagicMock()
    service.files().get().execute.return_value = {
        "id": "abc",
        "name": "Research",
        "parents": [],
    }

    path = _get_folder_path(service, "abc")
    assert path == "Research"


def test_get_folder_path_nested():
    """Should walk parent chain and build breadcrumb path."""
    service = MagicMock()

    calls = {
        "child": {"id": "child", "name": "Papers", "parents": ["parent"]},
        "parent": {"id": "parent", "name": "Research", "parents": []},
    }

    def fake_get(**kwargs):
        m = MagicMock()
        m.execute.return_value = calls[kwargs["fileId"]]
        return m

    service.files().get.side_effect = lambda **kw: fake_get(**kw)

    path = _get_folder_path(service, "child")
    assert path == "Research / Papers"


# ---------------------------------------------------------------------------
# list_files_in_folder — filtering
# ---------------------------------------------------------------------------


@patch("app.services.gdrive_service.build_drive_client")
@patch("app.services.gdrive_service._download_file")
@patch("app.services.gdrive_service._get_folder_path")
def test_list_files_returns_supported_files(mock_path, mock_download, mock_build):
    """Should return a FileRecord for each supported MIME type file."""
    mock_path.return_value = "Root / Folder"
    mock_download.return_value = b"fake content"

    service = MagicMock()
    service.files().list().execute.return_value = {
        "files": [
            {
                "id": "file-1",
                "name": "doc.pdf",
                "mimeType": "application/pdf",
                "modifiedTime": "2024-01-01T00:00:00Z",
            },
            {
                "id": "file-2",
                "name": "notes.txt",
                "mimeType": "text/plain",
                "modifiedTime": "2024-01-02T00:00:00Z",
            },
        ],
        "nextPageToken": None,
    }
    mock_build.return_value = service

    records = list_files_in_folder("folder-id")

    assert len(records) == 2
    assert records[0]["file_id"] == "file-1"
    assert records[0]["file_name"] == "doc.pdf"
    assert records[0]["content"] == b"fake content"
    assert records[0]["file_path"] == "Root / Folder / doc.pdf"


@patch("app.services.gdrive_service.build_drive_client")
@patch("app.services.gdrive_service._download_file")
@patch("app.services.gdrive_service._get_folder_path")
def test_list_files_skips_failed_downloads(mock_path, mock_download, mock_build):
    """Should skip a file if download raises, not abort the whole batch."""
    mock_path.return_value = "Root"
    mock_download.side_effect = [Exception("network error"), b"ok"]

    service = MagicMock()
    service.files().list().execute.return_value = {
        "files": [
            {
                "id": "bad",
                "name": "bad.pdf",
                "mimeType": "application/pdf",
                "modifiedTime": "",
            },
            {
                "id": "good",
                "name": "good.txt",
                "mimeType": "text/plain",
                "modifiedTime": "",
            },
        ],
        "nextPageToken": None,
    }
    mock_build.return_value = service

    records = list_files_in_folder("folder-id")
    # Only the successful download should be returned.
    assert len(records) == 1
    assert records[0]["file_id"] == "good"


# ---------------------------------------------------------------------------
# Supported MIME types set
# ---------------------------------------------------------------------------


def test_supported_mime_types_covered():
    """Ensure the four primary types are in the supported set."""
    assert "application/pdf" in SUPPORTED_MIME_TYPES
    assert "text/plain" in SUPPORTED_MIME_TYPES
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in SUPPORTED_MIME_TYPES
    )
    assert (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        in SUPPORTED_MIME_TYPES
    )


# ---------------------------------------------------------------------------
# Recursive traversal
# ---------------------------------------------------------------------------


@patch("app.services.gdrive_service._download_file")
def test_collect_files_recursive_enters_subfolders(mock_download):
    """_collect_files_recursive should descend into subfolders and collect files."""
    mock_download.return_value = b"data"

    service = MagicMock()

    # list() calls return different results depending on the query.
    def fake_list(**kwargs):
        q: str = kwargs.get("q", "")
        m = MagicMock()
        if "vnd.google-apps.folder" in q:
            # First call (root): return one subfolder.
            # Second call (subfolder): return no subfolders.
            if "root-id" in q:
                m.execute.return_value = {
                    "files": [{"id": "sub-id", "name": "Sub"}],
                    "nextPageToken": None,
                }
            else:
                m.execute.return_value = {"files": [], "nextPageToken": None}
        else:
            # File listing: one PDF wherever we are.
            m.execute.return_value = {
                "files": [
                    {
                        "id": "file-a",
                        "name": "a.pdf",
                        "mimeType": "application/pdf",
                        "modifiedTime": "2024-01-01T00:00:00Z",
                    }
                ],
                "nextPageToken": None,
            }
        return m

    service.files().list.side_effect = fake_list

    records: list = []
    _collect_files_recursive(
        service=service,
        folder_id="root-id",
        folder_path="Root",
        records=records,
        visited=set(),
    )

    # Should collect one file from root + one file from subfolder.
    assert len(records) == 2
    paths = {r["file_path"] for r in records}
    assert "Root / a.pdf" in paths
    assert "Root / Sub / a.pdf" in paths


def test_collect_files_recursive_guards_cycles():
    """_collect_files_recursive should not revisit already-visited folders."""
    service = MagicMock()  # Should never be called.
    records: list = []
    visited = {"duplicate-id"}

    # Calling with an already-visited ID should be a no-op.
    _collect_files_recursive(service, "duplicate-id", "X", records, visited)

    service.files.assert_not_called()
    assert records == []
