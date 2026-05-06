import logging
from typing import List, Optional

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.services.embedding.embedding_types import EmbeddedChunk

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing vector storage in Qdrant with hybrid search support."""

    def __init__(self):
        """Initialize the Qdrant client."""
        self.client = QdrantClient(
            url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME

    def create_collection(self) -> None:
        """Idempotently create the Qdrant collection with named dense and sparse vectors."""
        try:
            if self.client.collection_exists(self.collection_name):
                logger.info(
                    f"Collection '{self.collection_name}' already exists. Skipping creation."
                )
                return

            logger.info(
                f"Creating collection '{self.collection_name}' with hybrid search config..."
            )

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
            logger.info(f"Successfully created collection '{self.collection_name}'.")
        except Exception as e:
            logger.error(
                f"Failed to create collection '{self.collection_name}': {str(e)}"
            )
            raise

    def upsert_chunks(self, chunks: List[EmbeddedChunk]) -> None:
        """Batch upsert multiple chunks into Qdrant.

        Handles dense vectors for all chunks and adds sparse BM25 vectors for text content.
        """
        if not chunks:
            logger.warning("No chunks provided for upsert.")
            return

        points = []
        for chunk in chunks:
            try:
                # 1. Prepare vectors (Hybrid: Dense + Sparse)
                vectors = {"dense": chunk["dense_vector"]}

                # Only add sparse vector if it's not an image chunk
                if chunk["metadata"].get("content_type") != "image" and chunk.get(
                    "text"
                ):
                    vectors["sparse"] = models.Document(
                        text=chunk["text"], model="Qdrant/bm25"
                    )

                # 2. Prepare payload
                payload = {
                    "text": chunk["text"],
                    "file_id": chunk["metadata"]["file_id"],
                    "course_code": chunk["metadata"].get("course_code", ""),
                    "year": chunk["metadata"].get("year", ""),
                    "content_type": chunk["metadata"]["content_type"],
                    "source": chunk["metadata"]["source"],
                    "page_number": chunk["metadata"].get("page_number"),
                    # LLM Tags
                    "subject": chunk["tags"].get("subject", ""),
                    "topic": chunk["tags"].get("topic", ""),
                    "keywords": chunk["tags"].get("keywords", []),
                    "difficulty": chunk["tags"].get("difficulty", ""),
                }

                # Optional fields
                if "exam_type" in chunk["metadata"]:
                    payload["exam_type"] = chunk["metadata"]["exam_type"]
                if "video_id" in chunk["metadata"]:
                    payload["video_id"] = chunk["metadata"]["video_id"]
                if "parent_doc" in chunk["metadata"]:
                    payload["parent_doc"] = chunk["metadata"]["parent_doc"]

                points.append(
                    models.PointStruct(
                        id=chunk["chunk_id"], vector=vectors, payload=payload
                    )
                )
            except KeyError as e:
                logger.error(
                    f"Missing required field in chunk {chunk.get('chunk_id')}: {str(e)}"
                )
                continue

        if not points:
            logger.error("No valid points to upsert.")
            return

        try:
            self.client.upsert(
                collection_name=self.collection_name, points=points, wait=True
            )
            logger.info(
                f"Successfully upserted {len(points)} chunks to '{self.collection_name}'."
            )
        except Exception as e:
            logger.error(f"Failed to upsert chunks to Qdrant: {str(e)}")
            raise

    def search(
        self,
        query_vector: List[float],
        query_text: str,
        k: int = 5,
        course_code: Optional[str] = None,
        year: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
    ) -> List[dict]:
        """Perform a hybrid search using dense and sparse vectors, with optional metadata filtering."""
        
        must_conditions = []
        if course_code:
            must_conditions.append(
                models.FieldCondition(
                    key="course_code",
                    match=models.MatchValue(value=course_code),
                )
            )
        if year:
            must_conditions.append(
                models.FieldCondition(
                    key="year",
                    match=models.MatchValue(value=year),
                )
            )
        if subject:
            must_conditions.append(
                models.FieldCondition(
                    key="subject",
                    match=models.MatchValue(value=subject),
                )
            )
        if topic:
            must_conditions.append(
                models.FieldCondition(
                    key="topic",
                    match=models.MatchValue(value=topic),
                )
            )
        if difficulty:
            must_conditions.append(
                models.FieldCondition(
                    key="difficulty",
                    match=models.MatchValue(value=difficulty),
                )
            )
        if keywords:
            must_conditions.append(
                models.FieldCondition(
                    key="keywords",
                    match=models.MatchAny(any=keywords),
                )
            )
            
        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    models.Prefetch(
                        query=query_vector,
                        using="dense",
                        limit=k,
                    ),
                    models.Prefetch(
                        query=models.Document(text=query_text, model="Qdrant/bm25"),
                        using="sparse",
                        limit=k,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                query_filter=query_filter,
                limit=k,
            )
            
            return [hit.payload for hit in results.points]
            
        except Exception as e:
            logger.error(f"Failed to perform search: {str(e)}")
            raise
            

# Singleton instance
vector_store_service = VectorStoreService()
