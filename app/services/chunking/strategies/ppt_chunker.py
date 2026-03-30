# app/services/chunking/strategies/ppt_chunker.py

import logging
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker
from app.services.chunking.utils.splitting import split_words

logger = logging.getLogger(__name__)


class PPTChunker(BaseChunker):
    """
    Chunk a parsed PowerPoint document.

    Strategy:
    ┌──────────────────────────────────────────────────────────┐
    │  Each slide section → one or more text chunks            │
    │  Each table         → one table chunk                    │
    │  Each list block    → one list chunk                     │
    │  Each image         → one image chunk (no text, no mix)  │
    └──────────────────────────────────────────────────────────┘

    All chunk builders are inherited from BaseChunker.
    slide_number is forwarded into metadata as page_number.
    """

    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:

        chunks: List[Dict] = []

        text_idx = 0
        table_idx = 0
        list_idx = 0
        image_idx = 0

        try:
            # ── 1. Slide sections → text chunks ───────────────────────────
            for section in parsed_doc.get("sections", []):
                slide_number = section.get("slide_number")

                heading = (section.get("heading") or "").strip()
                content = (section.get("content") or "").strip()

                combined = "\n".join(filter(None, [heading, content]))
                if not combined:
                    continue

                for sub in split_words(combined, self.chunk_size, self.overlap):
                    chunk = self._build_chunk(file_id, text_idx, sub, metadata)
                    if slide_number is not None:
                        chunk["metadata"]["page_number"] = slide_number
                    chunks.append(chunk)
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
                        page_number=table.get("slide_number"),
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
                        page_number=lst.get("slide_number"),
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
                "PPT chunked file_id=%s → %d text, %d table, %d list, %d image chunks",
                file_id,
                text_idx,
                table_idx,
                list_idx,
                image_idx,
            )
            return chunks

        except Exception as exc:
            logger.exception("PPT chunking failed for file_id=%s: %s", file_id, exc)
            return []