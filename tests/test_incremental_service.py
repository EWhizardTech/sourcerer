"""Unit tests for incremental_service.py.

Uses pytest and unittest.mock to isolate the service from real Qdrant and SQLite files.
"""

import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# We patch settings BEFORE importing IncrementalService to ensure it uses our test config.
with patch("app.config.settings") as mock_settings:
    mock_settings.db_path = "data/test_sourcerer.db"
    mock_settings.qdrant_cluster_endpoint = "http://localhost:6333"
    mock_settings.qdrant_api_key = "test_key"
    mock_settings.qdrant_collection_name = "test_collection"
    mock_settings.qdrant_vector_size = 768
    mock_settings.qdrant_distance = "Cosine"

    from app.services.incremental_service import IncrementalService


@pytest.fixture
def service():
    """Fixture to provide a clean IncrementalService instance for each test."""
    test_db = Path("data/test_sourcerer.db")
    if test_db.exists():
        test_db.unlink()
    
    # Ensure data directory exists
    test_db.parent.mkdir(parents=True, exist_ok=True)
    
    # Mock QdrantClient to avoid network calls during init
    with patch("app.services.incremental_service.QdrantClient") as mock_qdrant_class:
        mock_client = mock_qdrant_class.return_value
        # Mock get_collections to return empty list so it tries to create one
        mock_client.get_collections.return_value.collections = []
        
        svc = IncrementalService()
        svc.qdrant_client = mock_client # Keep reference for assertions
        yield svc
    
    # Cleanup after test
    if test_db.exists():
        test_db.unlink()


def test_compute_hash(service: IncrementalService):
    """Should correctly compute MD5 hash of bytes."""
    content = b"sourcerer"
    # md5("sourcerer") = 36a464b753fa042bee01b3e0180f6030
    expected = "36a464b753fa042bee01b3e0180f6030"
    assert service.compute_hash(content) == expected


def test_check_file_status_new(service: IncrementalService):
    """Should return NEW if file_id is not in DB."""
    assert service.check_file_status("non-existent", "some-hash") == "NEW"


def test_check_file_status_skip(service: IncrementalService):
    """Should return SKIP if hash matches stored version."""
    service.update_tracking_record("file-1", "hash-a")
    assert service.check_file_status("file-1", "hash-a") == "SKIP"


def test_check_file_status_update(service: IncrementalService):
    """Should return UPDATE if hash differs from stored version."""
    service.update_tracking_record("file-1", "hash-a")
    assert service.check_file_status("file-1", "hash-b") == "UPDATE"


def test_delete_existing_vectors(service: IncrementalService):
    """Should call Qdrant delete with correct filter."""
    service.delete_existing_vectors("file-123")
    
    # Verify qdrant_client.delete was called with filter for file_id
    service.qdrant_client.delete.assert_called_once()
    args, kwargs = service.qdrant_client.delete.call_args
    assert kwargs["collection_name"] == "test_collection"
    # Check if file_id filter is present
    filter_obj = kwargs["points_selector"].filter
    assert filter_obj.must[0].key == "file_id"
    assert filter_obj.must[0].match.value == "file-123"


def test_update_tracking_record(service: IncrementalService):
    """Should persist the record to SQLite."""
    service.update_tracking_record("file-99", "final-hash")
    
    with sqlite3.connect(service.db_path) as conn:
        cursor = conn.execute("SELECT file_hash FROM file_tracking WHERE file_id = ?", ("file-99",))
        row = cursor.fetchone()
    
    assert row is not None
    assert row[0] == "final-hash"


def test_ensure_collection_exists_creates_if_missing(service: IncrementalService):
    """Initialization should trigger collection creation if missing."""
    # This was actually called during __init__ in the fixture
    service.qdrant_client.create_collection.assert_called_once()
    assert service.qdrant_client.create_collection.call_args.kwargs["collection_name"] == "test_collection"
