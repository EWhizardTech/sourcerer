# app/services/chunking/types.py

from typing import Any, Dict, List, Optional, TypedDict


class ImageRef(TypedDict):
    image_id: str
    image_bytes: str  # base64-encoded


class ChunkMetadata(TypedDict, total=False):
    file_id: str
    source: str  # "document" | "transcript"
    content_type: str  # "text" | "table" | "list" | "image"
    page_number: Optional[int]
    course_code: str
    year: str
    # LLM tags (added downstream by tagging service)
    subject: str
    topic: str
    keywords: List[str]
    difficulty: str


class TextChunk(TypedDict):
    """Text, table, or list chunk — always has 'text', never has 'image'."""

    chunk_id: str
    text: str
    metadata: ChunkMetadata


class ImageChunk(TypedDict):
    """Image chunk — NO 'text' key per spec."""

    chunk_id: str
    image: ImageRef
    metadata: ChunkMetadata


# Union type used as the return type of all chunkers
Chunk = TextChunk | ImageChunk
