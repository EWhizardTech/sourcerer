# app/services/chunking/strategies/section_chunker.py

import logging
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker
from app.services.chunking.utils.splitting import split_words

logger = logging.getLogger(__name__)


class SectionChunker(BaseChunker):
    """
    Chunk based on sections first, then split inside sections.

    MUCH better for RAG quality.
    """

    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:
        try:
            sections = parsed_doc.get("sections", [])

            if not sections:
                logger.warning("No sections found, falling back to word chunking")
                return []

            chunks = []
            idx = 0

            for section in sections:
                content = section.get("content", "")

                if isinstance(content, list):
                    content = "\n".join(content)

                sub_chunks = split_words(content, self.chunk_size, self.overlap)

                for sub in sub_chunks:
                    chunks.append(self._build_chunk(file_id, idx, sub, metadata))
                    idx += 1

            return chunks

        except Exception as exc:
            logger.exception("Section chunking failed for file_id=%s: %s", file_id, exc)
            return []
