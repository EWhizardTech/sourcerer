"""Hybrid retrieval service built on the Qdrant Query API.

Uses adapter pattern so additional vector backends can be added without
changing callers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from google import genai
from google.genai import types
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import (ResponseHandlingException,
                                           UnexpectedResponse)

from app.core.config import settings

logger = logging.getLogger(__name__)


class RetrievalAdapter(ABC):
    """Abstract adapter for retrieval backends."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve top-k chunks for a query."""


class QdrantRetrievalAdapter(RetrievalAdapter):
    """Qdrant implementation using dense + sparse fusion search."""

    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.embedding_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.embedding_model = "gemini-embedding-2-preview"
        self._payload_indexes_ready = False

    def _ensure_payload_indexes(self) -> None:
        """Create payload indexes used by retrieval filters, if missing."""
        if self._payload_indexes_ready:
            return

        index_specs = {
            "course_code": models.PayloadSchemaType.KEYWORD,
            "year": models.PayloadSchemaType.KEYWORD,
            "keywords": models.PayloadSchemaType.KEYWORD,
            "topic": models.PayloadSchemaType.KEYWORD,
            "subject": models.PayloadSchemaType.KEYWORD,
        }

        for field_name, field_schema in index_specs.items():
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                    wait=True,
                )
            except (ResponseHandlingException, UnexpectedResponse) as exc:
                message = str(exc)
                if "already exists" in message.lower():
                    continue

                logger.warning(
                    "Could not create payload index for '%s': %s",
                    field_name,
                    message,
                )

        self._payload_indexes_ready = True

    def _embed_query_dense(self, query: str) -> list[float]:
        """Create a dense query vector using the same embedding family as ingestion."""
        try:
            response = self.embedding_client.models.embed_content(
                model=self.embedding_model,
                contents=[query],
                config=types.EmbedContentConfig(
                    output_dimensionality=settings.QDRANT_VECTOR_SIZE,
                ),
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Failed to generate dense embedding: {exc}") from exc

        if not response.embeddings:
            raise ValueError("No dense embedding returned for query")
        return response.embeddings[0].values

    def _build_filter(self, filters: dict[str, Any] | None) -> models.Filter | None:
        """Build payload filter from request filters.

        Tag filtering is mapped to LLM-generated payload tags in Qdrant:
        - keywords
        - topic
        - subject
        """
        if not filters:
            return None

        must_conditions: list[models.Condition] = []

        course_code = filters.get("course_code")
        if course_code:
            must_conditions.append(
                models.FieldCondition(
                    key="course_code",
                    match=models.MatchValue(value=course_code),
                )
            )

        year = filters.get("year")
        if year:
            must_conditions.append(
                models.FieldCondition(
                    key="year",
                    match=models.MatchValue(value=year),
                )
            )

        tags = filters.get("tags") or []
        if tags:
            # Require every requested tag to match tagging payload fields.
            for tag in tags:
                must_conditions.append(
                    models.Filter(
                        should=[
                            models.FieldCondition(
                                key="keywords",
                                match=models.MatchValue(value=tag),
                            ),
                            models.FieldCondition(
                                key="topic",
                                match=models.MatchValue(value=tag),
                            ),
                            models.FieldCondition(
                                key="subject",
                                match=models.MatchValue(value=tag),
                            ),
                        ]
                    )
                )

        if not must_conditions:
            return None

        return models.Filter(must=must_conditions)

    @staticmethod
    def _to_result(point: models.ScoredPoint) -> dict[str, Any]:
        """Normalize Qdrant point into retrieval response shape."""
        payload = point.payload or {}
        return {
            "chunk_id": str(point.id),
            "text": payload.get("text", ""),
            "score": point.score,
            "metadata": {
                "file_id": payload.get("file_id", ""),
                "course_code": payload.get("course_code", ""),
                "year": payload.get("year", ""),
                "content_type": payload.get("content_type", ""),
                "source": payload.get("source", ""),
                "page_number": payload.get("page_number"),
                "exam_type": payload.get("exam_type"),
                "video_id": payload.get("video_id"),
                "parent_doc": payload.get("parent_doc"),
            },
            "tags": {
                "subject": payload.get("subject", ""),
                "topic": payload.get("topic", ""),
                "keywords": payload.get("keywords", []),
                "difficulty": payload.get("difficulty", ""),
            },
        }

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Run hybrid retrieval using Qdrant Query API with RRF fusion.

        Example hybrid query call:
            retrieval_service.retrieve_chunks(
                query="Explain recursion",
                filters={"course_code": "CS101", "year": "2026", "tags": ["recursion"]},
                top_k=5,
            )
        """
        dense_query = self._embed_query_dense(query)
        payload_filter = self._build_filter(filters)

        prefetch_dense = models.Prefetch(
            query=dense_query,
            using="dense",
            limit=top_k,
            filter=payload_filter,
        )
        prefetch_sparse = models.Prefetch(
            query=models.Document(text=query, model="Qdrant/bm25"),
            using="sparse",
            limit=top_k,
            filter=payload_filter,
        )

        if payload_filter is not None:
            self._ensure_payload_indexes()

        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[prefetch_dense, prefetch_sparse],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
                with_payload=True,
            )
        except UnexpectedResponse as exc:
            message = str(exc)
            if "Index required but not found" in message:
                logger.info(
                    "Qdrant requires payload index for filter fields. Creating indexes and retrying once."
                )
                self._payload_indexes_ready = False
                self._ensure_payload_indexes()
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    prefetch=[prefetch_dense, prefetch_sparse],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=top_k,
                    with_payload=True,
                )
            else:
                raise ValueError(f"Qdrant query failed: {message}") from exc
        except ResponseHandlingException as exc:
            message = str(exc)
            if "getaddrinfo failed" in message:
                raise ValueError(
                    "Unable to resolve Qdrant host. Check QDRANT_URL DNS/network and internet access."
                ) from exc

            raise ValueError(f"Qdrant query failed: {message}") from exc

        return [self._to_result(point) for point in response.points]


class RetrievalService:
    """Facade used by routes and other services."""

    def __init__(self, adapter: RetrievalAdapter | None = None) -> None:
        self.adapter = adapter

    def _get_adapter(self) -> RetrievalAdapter:
        """Initialize default adapter lazily when needed."""
        if self.adapter is None:
            self.adapter = QdrantRetrievalAdapter()
        return self.adapter

    def retrieve_chunks(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve top-k chunks from the configured adapter."""
        adapter = self._get_adapter()
        return adapter.retrieve(query=query, filters=filters, top_k=top_k)


retrieval_service = RetrievalService()


def retrieve_chunks(
    query: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Module-level helper for compatibility with existing call style."""
    return retrieval_service.retrieve_chunks(query=query, filters=filters, top_k=top_k)
