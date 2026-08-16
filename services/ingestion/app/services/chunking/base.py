# app/services/chunking/base.py

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """
    Abstract chunker.

    Responsibilities:
    - Accept parsed_doc
    - Return list of chunks
    - Never crash (fail gracefully)

    Shared builders (all strategies inherit):
    - _build_chunk()        → text chunk
    - _build_typed_chunk()  → table / list chunk
    - _build_image_chunk()  → image chunk  (NO text key)
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    @abstractmethod
    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:
        pass

    def _build_chunk(
        self, file_id: str, idx: int, text: str, metadata: Dict[str, Any]
    ) -> Dict:
        """Text chunk — content_type always 'text'."""
        original_id = f"{file_id}_text_{idx}"
        return {
            "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, original_id)),
            "text": text,
            "metadata": {
                **metadata,
                "file_id": file_id,
                "content_type": "text",
                "source": metadata.get("source", "document"),
            },
        }

    def _build_typed_chunk(
        self,
        file_id: str,
        content_type: str,
        idx: int,
        text: str,
        metadata: Dict[str, Any],
        page_number: Optional[int] = None,
    ) -> Dict:
        """Table / list chunk — content_type is caller-supplied."""
        chunk_meta = {
            **metadata,
            "file_id": file_id,
            "content_type": content_type,
            "source": metadata.get("source", "document"),
        }
        if page_number is not None:
            chunk_meta["page_number"] = page_number

        original_id = f"{file_id}_{content_type}_{idx}"
        return {
            "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, original_id)),
            "text": text,
            "metadata": chunk_meta,
        }

    def _build_image_chunk(
        self,
        file_id: str,
        idx: int,
        image: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict:
        """
        Image chunk — NO 'text' key per spec (3-chunking.md).

        Shape:
        {
            "chunk_id": <uuid>,
            "image": { "image_id": "...", "image_bytes": "..." },
            "metadata": {
                "file_id": "...",
                "source": "document",
                "content_type": "image",
                "page_number": ...,
                "course_code": "...",   # forwarded from folder metadata
                "year": "...",          # forwarded from folder metadata
                ...
            }
        }
        """
        original_id = f"{file_id}_image_{idx}"
        return {
            "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, original_id)),
            "image": {
                "image_id": image.get("image_id"),
                "image_bytes": image.get("image_bytes"),
            },
            "metadata": {
                **metadata,  # course_code, year, tags, etc.
                "file_id": file_id,
                "source": "document",
                "content_type": "image",
                "page_number": image.get("page_number"),
            },
        }
