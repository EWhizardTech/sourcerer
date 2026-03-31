# app/services/tagging/types.py

from typing import List, Optional, TypedDict
from app.services.chunking.types import ChunkMetadata, ImageRef


class TagSchema(TypedDict):
    """Schema for LLM-generated tags."""
    subject: str
    topic: str
    keywords: List[str]
    difficulty: str


class TaggedChunk(TypedDict):
    """Output of the tagging stage.
    
    Preserves original structure but adds a separate 'tags' key.
    Includes 'text' (empty for images) and 'image' (None for text) 
    to facilitate Stage 5 embedding.
    """
    chunk_id: str
    text: str
    image: Optional[ImageRef]
    metadata: ChunkMetadata
    tags: TagSchema
