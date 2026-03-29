import logging
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker
from app.services.chunking.utils.splitting import split_words

logger = logging.getLogger(__name__)


class PDFChunker(BaseChunker):
    """
    Chunk PDF intelligently:
    - Sections → primary
    - Tables → separate chunks
    - Lists → separate chunks
    """

    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:

        chunks = []
        idx = 0

        try:
            # 1. Sections
            for section in parsed_doc.get("sections", []):
                text = "\n".join(
                    filter(None, [section.get("heading"), section.get("content")])
                )

                sub_chunks = split_words(text, self.chunk_size, self.overlap)

                for sub in sub_chunks:
                    chunks.append(self._build_chunk(file_id, idx, sub, metadata))
                    idx += 1

            # 2. Tables
            for table in parsed_doc.get("tables", []):
                chunks.append(
                    self._build_chunk(
                        file_id,
                        idx,
                        table["content"],
                        {**metadata, "content_type": "table"},
                    )
                )
                idx += 1

            # 3. Lists
            for lst in parsed_doc.get("lists", []):
                chunks.append(
                    self._build_chunk(
                        file_id,
                        idx,
                        lst["content"],
                        {**metadata, "content_type": "list"},
                    )
                )
                idx += 1

            return chunks

        except Exception as exc:
            logger.exception("PDF chunking failed: %s", exc)
            return []