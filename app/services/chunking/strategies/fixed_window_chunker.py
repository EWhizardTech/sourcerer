# app/services/chunking/strategies/word_chunker.py

import logging
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker
from app.services.chunking.utils.splitting import split_words

logger = logging.getLogger(__name__)


class FixedWindowChunker(BaseChunker):
    """
    Default chunking:
    - word-based
    - overlapping
    """

    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:
        try:
            text = parsed_doc.get("text", "")

            if not text.strip():
                logger.warning("Empty text for file_id=%s", file_id)
                return []

            split_chunks = split_words(text, self.chunk_size, self.overlap)

            chunks = [
                self._build_chunk(file_id, idx, chunk, metadata)
                for idx, chunk in enumerate(split_chunks)
            ]

            logger.debug("Chunked file %s into %d chunks", file_id, len(chunks))

            return chunks

        except Exception as exc:
            logger.exception("Chunking failed for file_id=%s: %s", file_id, exc)
            return []
