# app/services/chunking/base.py

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """
    Abstract chunker.

    Responsibilities:
    - Accept parsed_doc
    - Return list of chunks
    - Never crash (fail gracefully)
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
        return {
            "chunk_id": f"{file_id}_text_{idx}",
            "text": text,
            "metadata": {
                **metadata,
                "file_id": file_id,
                "content_type": "text",
            },
        }
