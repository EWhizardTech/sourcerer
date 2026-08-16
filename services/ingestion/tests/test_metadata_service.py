"""Unit tests for metadata_service.py."""

import pytest

from app.services.metadata_service import extract_folder_metadata


def test_extract_folder_metadata_basic():
    """Should extract tags correctly from a standard path."""
    file_path = "Root / Folder / Sub / file.pdf"
    metadata = extract_folder_metadata(file_path, course_code="CS101", year="2024")

    assert metadata["course_code"] == "CS101"
    assert metadata["year"] == "2024"
    # Root is excluded by default
    assert metadata["tags"] == ["folder", "sub"]


def test_extract_folder_metadata_include_root():
    """Should include root folder if include_root is True."""
    file_path = "Root / Folder / Sub / file.pdf"
    metadata = extract_folder_metadata(file_path, include_root=True)

    assert metadata["tags"] == ["root", "folder", "sub"]


def test_extract_folder_metadata_no_folders():
    """Should return empty tags if only root and filename are present."""
    file_path = "Root / file.pdf"
    metadata = extract_folder_metadata(file_path, include_root=False)
    assert metadata["tags"] == []


def test_extract_folder_metadata_normalization():
    """Should lowercase and strip tags."""
    file_path = "  My Folder  /  SubFolder  /  File.PDF  "
    metadata = extract_folder_metadata(file_path)
    # Exclude root "my folder", tags should be ["subfolder"]
    assert metadata["tags"] == ["subfolder"]


def test_extract_folder_metadata_with_empty_segments():
    """Should filter out empty segments."""
    file_path = "Root / / Sub / file.pdf"
    metadata = extract_folder_metadata(file_path)
    assert metadata["tags"] == ["sub"]


def test_extract_folder_metadata_deterministic_output():
    """Should return exactly what's provided for course/year."""
    file_path = "Path / File.txt"
    metadata = extract_folder_metadata(file_path, course_code="X", year="Y")
    assert metadata["course_code"] == "X"
    assert metadata["year"] == "Y"
