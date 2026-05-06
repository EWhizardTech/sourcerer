"""Structured retrieval helper used by the quiz pipeline.

This service shares the same embedding and vector store stack used by the
document retrieval flow, but returns structured chunks so the quiz generator
can build MCQs from actual retrieved content.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.embedding.embedding_service import embedding_service
from app.services.vector_store.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)


class RetrievalService:
    """Retrieve structured chunks from the shared vector store."""

    def retrieve_chunks(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search the indexed corpus and return structured chunk payloads."""
        filters = filters or {}
        query_text = query.strip()
        if not query_text:
            return []

        query_vector = embedding_service.embed_query(query_text)
        if not query_vector:
            logger.warning("Failed to embed retrieval query: %s", query_text)
            return []

        results = vector_store_service.search(
            query_vector=query_vector,
            query_text=query_text,
            k=top_k,
            course_code=filters.get("course_code"),
            year=filters.get("year"),
            subject=filters.get("subject"),
            topic=filters.get("topic"),
            keywords=filters.get("tags") or filters.get("keywords"),
            difficulty=filters.get("difficulty"),
        )

        structured_results: list[dict[str, Any]] = []
        for index, payload in enumerate(results):
            structured_results.append(
                {
                    "chunk_id": str(payload.get("chunk_id", index)),
                    "text": payload.get("text", ""),
                    "source": payload.get("source", "Unknown"),
                    "page_number": payload.get("page_number"),
                    "file_id": payload.get("file_id", ""),
                    "course_code": payload.get("course_code", ""),
                    "year": payload.get("year", ""),
                    "tags": {
                        "subject": payload.get("subject", ""),
                        "topic": payload.get("topic", ""),
                        "keywords": payload.get("keywords", []),
                        "difficulty": payload.get("difficulty", ""),
                    },
                }
            )

        return structured_results


retrieval_service = RetrievalService()