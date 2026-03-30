# app/services/chunking/strategies/docx_chunker.py

import logging
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker
from app.services.chunking.utils.splitting import split_words

logger = logging.getLogger(__name__)


class DOCXChunker(BaseChunker):
    """
    Chunk a parsed DOCX document.

    Strategy:
    ┌──────────────────────────────────────────────────────────┐
    │  Each section  → one or more text chunks                 │
    │  Each table    → one table chunk                         │
    │  Each list     → one list chunk                          │
    │  Each image    → one image chunk  (no text, no mix)      │
    └──────────────────────────────────────────────────────────┘

    Chunk-ID format  (deterministic):
        <file_id>_text_<idx>
        <file_id>_table_<idx>
        <file_id>_list_<idx>
        <file_id>_image_<idx>

    Rules:
    - NEVER mix image bytes with text in the same chunk
    - Sections wider than chunk_size are split with word-window + overlap
    - page_number is None for DOCX (no page concept at parse time)
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
            # ── 1. Sections → text chunks ─────────────────────────────────
            for section in parsed_doc.get("sections", []):
                heading = (section.get("heading") or "").strip()
                content = (section.get("content") or "").strip()

                combined = "\n".join(filter(None, [heading, content]))
                if not combined:
                    continue

                sub_chunks = split_words(combined, self.chunk_size, self.overlap)
                for sub in sub_chunks:
                    chunks.append(
                        self._build_text_chunk(
                            file_id=file_id,
                            idx=text_idx,
                            text=sub,
                            metadata=metadata,
                        )
                    )
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
                "DOCX chunked file_id=%s → %d text, %d table, %d list, %d image chunks",
                file_id,
                text_idx,
                table_idx,
                list_idx,
                image_idx,
            )
            return chunks

        except Exception as exc:
            logger.exception("DOCX chunking failed for file_id=%s: %s", file_id, exc)
            return []

    # ------------------------------------------------------------------ #
    # Chunk builders
    # ------------------------------------------------------------------ #

    def _build_text_chunk(
        self,
        file_id: str,
        idx: int,
        text: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "chunk_id": f"{file_id}_text_{idx}",
            "text": text,
            "metadata": {
                **metadata,
                "file_id": file_id,
                "content_type": "text",
                "source": "document",
                "page_number": None,   # DOCX has no page-level concept
            },
        }

    def _build_typed_chunk(
        self,
        file_id: str,
        content_type: str,   # "table" | "list"
        idx: int,
        text: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "chunk_id": f"{file_id}_{content_type}_{idx}",
            "text": text,
            "metadata": {
                **metadata,
                "file_id": file_id,
                "content_type": content_type,
                "source": "document",
                "page_number": None,
            },
        }

    def _build_image_chunk(
        self,
        file_id: str,
        idx: int,
        image: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Image chunks carry NO text.
        Structure mirrors the spec in 3-chunking.md exactly.
        """
        return {
            "chunk_id": f"{file_id}_image_{idx}",
            "text": "",          # intentionally empty — embed via image bytes
            "image": {
                "image_id": image.get("image_id"),
                "image_bytes": image.get("image_bytes"),
            },
            "metadata": {
                **metadata,
                "file_id": file_id,
                "content_type": "image",
                "source": "document",
                "page_number": image.get("page_number"),   # None for DOCX
            },
        }