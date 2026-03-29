# app/services/chunking/types.py

from typing import Any, Dict, TypedDict


class Chunk(TypedDict):
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
