# app/services/embedding/embedding_service.py

import base64
import logging
from typing import List

from google import genai
from google.genai import types

from sourcerer_core.config import settings
from sourcerer_core.embedding.embedding_types import EmbeddedChunk, TaggedChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating dense vectors using Gemini Embeddings 2 via Vertex AI."""

    def __init__(self):
        """Initialize the Gemini client for Vertex AI."""
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-embedding-2-preview"

    def _get_description_from_tags(self, tags: dict) -> str:
        """Helper to create a combined description from tags."""
        parts = []
        if tags.get("subject"):
            parts.append(f"Subject: {tags['subject']}")
        if tags.get("topic"):
            parts.append(f"Topic: {tags['topic']}")
        if tags.get("keywords"):
            parts.append(f"Keywords: {', '.join(tags['keywords'])}")
        return " | ".join(parts) if parts else "Educational content"

    def embed_chunks(self, chunks: List[TaggedChunk]) -> List[EmbeddedChunk]:
        """Generate dense vectors for a list of tagged chunks using combined multimodal embeddings.

        Args:
            chunks: List of TaggedChunk objects.

        Returns:
            List of EmbeddedChunk objects with 3072-dim vectors.
        """
        embedded_chunks: List[EmbeddedChunk] = []

        for chunk in chunks:
            try:
                # 1. Prepare contents for this chunk
                # native multimodal allows mixing types in counts
                content_parts = []

                description = self._get_description_from_tags(chunk.get("tags", {}))

                if chunk.get("text"):
                    # Combine original text with tags for better semantic alignment
                    full_text = f"{description}\n\n{chunk['text']}"
                    content_parts.append(full_text)

                if chunk.get("image") is not None:
                    # Multimodal combined embedding
                    img_ref = chunk["image"]
                    img_b64 = img_ref["image_bytes"]
                    img_data = base64.b64decode(img_b64)

                    if len(img_data) > settings.MAX_IMAGE_EMBEDDING_SIZE:
                        logger.warning(
                            f"Image chunk {chunk['chunk_id']} exceeds max size "
                            f"({len(img_data)} > {settings.MAX_IMAGE_EMBEDDING_SIZE}). Skipping."
                        )
                        continue

                    # If this is an image-only chunk (no text), ensure we have a prompt/tags
                    if not content_parts:
                        content_parts.append(
                            description
                            if description
                            else "What is shown in this image?"
                        )

                    content_parts.append(
                        types.Part.from_bytes(data=img_data, mime_type="image/jpeg")
                    )

                if not content_parts:
                    logger.warning(
                        f"Chunk {chunk['chunk_id']} has no text or image content. Skipping."
                    )
                    continue

                # 2. Call Vertex AI
                # Note: gemini-embedding-2-preview uses content_parts as a single entry in contents list
                # to get one embedding for the combination.
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=content_parts,
                    config=types.EmbedContentConfig(
                        output_dimensionality=settings.QDRANT_VECTOR_SIZE
                    ),
                )

                if response.embeddings:
                    embedded_chunks.append(
                        {**chunk, "dense_vector": response.embeddings[0].values}
                    )
                else:
                    logger.warning(
                        f"No embeddings returned for chunk {chunk['chunk_id']}"
                    )

            except Exception as e:
                logger.error(f"Failed to embed chunk {chunk.get('chunk_id')}: {str(e)}")

        return embedded_chunks

    def embed_query(self, query: str) -> List[float]:
        """Generate dense vector for a search query string."""
        try:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=query,
                config=types.EmbedContentConfig(
                    output_dimensionality=settings.QDRANT_VECTOR_SIZE,
                    task_type="RETRIEVAL_QUERY"
                ),
            )
            if response.embeddings:
                return response.embeddings[0].values
            else:
                logger.error(f"No embeddings returned for query: {query}")
                return []
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            raise

# Singleton instance
embedding_service = EmbeddingService()
