"""Incremental processing service for Sourcerer.

Handles file hashing, tracking file processing status in SQLite,
and managing vector deletion in Qdrant for updated files.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient, models

from app.core.config import settings

logger = logging.getLogger(__name__)


class IncrementalService:
    """Service to handle incremental file processing logic."""

    def __init__(self):
        self.db_path = Path(settings.db_path)
        self._init_db()
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_cluster_endpoint,
            api_key=settings.qdrant_api_key,
        )
        self.collection_name = settings.qdrant_collection_name
        self._ensure_collection_exists()

    def _init_db(self):
        """Initialize SQLite database and tracking table."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_tracking (
                    file_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    last_processed_at TEXT NOT NULL
                )
                """)
            conn.commit()
        logger.info("Initialized tracking database at %s", self.db_path)

    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists before operations."""
        try:
            collections = self.qdrant_client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info("Creating Qdrant collection: %s", self.collection_name)
                # Default vector size and distance from config
                distance_map = {
                    "Cosine": models.Distance.COSINE,
                    "Euclid": models.Distance.EUCLID,
                    "Dot": models.Distance.DOT,
                }
                distance = distance_map.get(
                    settings.qdrant_distance, models.Distance.COSINE
                )

                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=settings.qdrant_vector_size,
                        distance=distance,
                    ),
                )
            else:
                logger.info("Qdrant collection %s already exists", self.collection_name)
        except Exception as exc:
            logger.error("Failed to check/create Qdrant collection: %s", exc)
            # We don't raise here to allow the service to be initialized even if Qdrant is down,
            # though downstream operations will fail.

    def compute_hash(self, content: bytes) -> str:
        """Compute MD5 hash of raw file content."""
        return hashlib.md5(content).hexdigest()

    def check_file_status(self, file_id: str, file_hash: str) -> str:
        """Determine if a file is NEW, SKIP, or UPDATE.

        Args:
            file_id: Stable identifier for the file.
            file_hash: Current computed hash of the file content.

        Returns:
            "NEW", "SKIP", or "UPDATE".
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT file_hash FROM file_tracking WHERE file_id = ?", (file_id,)
            )
            row = cursor.fetchone()

        if not row:
            return "NEW"

        stored_hash = row[0]
        if stored_hash == file_hash:
            return "SKIP"

        return "UPDATE"

    def delete_existing_vectors(self, file_id: str):
        """Delete existing vectors for a file from Qdrant.

        Args:
            file_id: File ID to filter by in Qdrant point payloads.
        """
        logger.info(
            "Deleting existing vectors for file_id=%s from %s",
            file_id,
            self.collection_name,
        )
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="file_id",
                                match=models.MatchValue(value=file_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            logger.error("Failed to delete vectors from Qdrant: %s", exc)
            raise

    def update_tracking_record(self, file_id: str, file_hash: str):
        """Update tracking store with new hash and timestamp.

        Should only be called AFTER successful processing of the file.
        """
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_tracking (file_id, file_hash, last_processed_at)
                VALUES (?, ?, ?)
                """,
                (file_id, file_hash, now),
            )
            conn.commit()
        logger.info("Updated tracking record for file_id=%s", file_id)


# Singleton instance for the service.
incremental_service = IncrementalService()
