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

from sourcerer_core.config import settings

logger = logging.getLogger(__name__)


class IncrementalService:
    """Service to handle incremental file processing logic."""

    def __init__(self):
        self.db_path = Path(settings.DB_PATH)
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.initialized = False
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensures that the tracking database and vector collection exist."""
        # 1. Tracking Database (SQLite)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_tracking (
                    file_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # 2. Vector Collection (Qdrant)
        try:
            if not self.qdrant_client.collection_exists(self.collection_name):
                # Map human-readable distance to Qdrant models
                distance_map = {
                    "Cosine": models.Distance.COSINE,
                    "Euclidean": models.Distance.EUCLID,
                    "Dot": models.Distance.DOT,
                }
                distance = distance_map.get(
                    settings.QDRANT_DISTANCE, models.Distance.COSINE
                )

                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=settings.QDRANT_VECTOR_SIZE, distance=distance
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams(
                            modifier=models.Modifier.IDF
                        )
                    },
                )
            else:
                logger.info("Qdrant collection %s already exists", self.collection_name)
        except Exception as exc:
            logger.error("Failed to check/create Qdrant collection: %s", exc)

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
