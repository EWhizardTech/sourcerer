# app/services/chunking/strategies/pdf_chunker.py

import logging
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker
from app.services.chunking.utils.splitting import split_words

logger = logging.getLogger(__name__)


class PDFChunker(BaseChunker):
    """
    Chunk PDF intelligently:
    - Sections  → text chunks     (split_words if over chunk_size)
    - Tables    → table chunks    (one per table)
    - Lists     → list chunks     (one per list block)
    - Images    → image chunks    (no text, no mix)
    """

    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:

        chunks: List[Dict] = []

        # Separate counters per type → deterministic, non-colliding chunk_ids
        text_idx = 0
        table_idx = 0
        list_idx = 0
        image_idx = 0

        try:
            # ── 1. Sections → text chunks ─────────────────────────────────
            for section in parsed_doc.get("sections", []):
                text = "\n".join(
                    filter(None, [section.get("heading"), section.get("content")])
                )
                if not text.strip():
                    continue

                for sub in split_words(text, self.chunk_size, self.overlap):
                    chunks.append(self._build_chunk(file_id, text_idx, sub, metadata))
                    text_idx += 1

            # ── 2. Tables ─────────────────────────────────────────────────
            for table in parsed_doc.get("tables", []):
                content = (table.get("content") or "").strip()
                if not content:
                    continue

                chunks.append(
                    self._build_typed_chunk(
                        file_id=file_id,
                        content_type="table",
                        idx=table_idx,
                        text=content,
                        metadata=metadata,
                    )
                )
                table_idx += 1

            # ── 3. Lists ──────────────────────────────────────────────────
            for lst in parsed_doc.get("lists", []):
                content = (lst.get("content") or "").strip()
                if not content:
                    continue

                chunks.append(
                    self._build_typed_chunk(
                        file_id=file_id,
                        content_type="list",
                        idx=list_idx,
                        text=content,
                        metadata=metadata,
                    )
                )
                list_idx += 1

            # ── 4. Images → image chunks (no text) ───────────────────────
            for image in parsed_doc.get("images", []):
                chunks.append(
                    self._build_image_chunk(
                        file_id=file_id,
                        idx=image_idx,
                        image=image,
                        metadata=metadata,
                    )
                )
                image_idx += 1

            logger.debug(
                "PDF chunked file_id=%s → %d text, %d table, %d list, %d image chunks",
                file_id,
                text_idx,
                table_idx,
                list_idx,
                image_idx,
            )
            return chunks

        except Exception as exc:
            logger.exception("PDF chunking failed for file_id=%s: %s", file_id, exc)
            return []