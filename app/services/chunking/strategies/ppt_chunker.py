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
    │  Each table in the doc → one table chunk                 │
    │  Each list block → one list chunk                        │
    │  Each image → one image chunk  (no text, no embedding)  │
    └──────────────────────────────────────────────────────────┘

    Chunk-ID format  (deterministic):
        <file_id>_text_<idx>
        <file_id>_table_<idx>
        <file_id>_list_<idx>
        <file_id>_image_<idx>

    Rules:
    - NEVER mix image bytes with text in the same chunk
    - Sections wider than chunk_size are split with word-window + overlap
    - slide_number is forwarded into metadata when present
    """

    def chunk(
        self, parsed_doc: Dict[str, Any], metadata: Dict[str, Any], file_id: str
    ) -> List[Dict]:

        chunks: List[Dict] = []

        # independent counters per content type for stable IDs
        text_idx = 0
        table_idx = 0
        list_idx = 0
        image_idx = 0

        try:
            # ── 1. Slide sections → text chunks ──────────────────────────
            for section in parsed_doc.get("sections", []):
                slide_number = section.get("slide_number")

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
                            slide_number=slide_number,
                        )
                    )
                    text_idx += 1

            # ── 2. Tables ─────────────────────────────────────────────────
            for table in parsed_doc.get("tables", []):
                content = (table.get("content") or "").strip()
                if not content:
                    continue

                slide_number = table.get("slide_number")
                chunks.append(
                    self._build_typed_chunk(
                        file_id=file_id,
                        content_type="table",
                        idx=table_idx,
                        text=content,
                        metadata=metadata,
                        slide_number=slide_number,
                    )
                )
                table_idx += 1

            # ── 3. Lists ──────────────────────────────────────────────────
            for lst in parsed_doc.get("lists", []):
                content = (lst.get("content") or "").strip()
                if not content:
                    continue

                slide_number = lst.get("slide_number")
                chunks.append(
                    self._build_typed_chunk(
                        file_id=file_id,
                        content_type="list",
                        idx=list_idx,
                        text=content,
                        metadata=metadata,
                        slide_number=slide_number,
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

    # ------------------------------------------------------------------ #
    # Chunk builders
    # ------------------------------------------------------------------ #

    def _build_text_chunk(
        self,
        file_id: str,
        idx: int,
        text: str,
        metadata: Dict[str, Any],
        slide_number: int | None,
    ) -> Dict[str, Any]:
        chunk_meta = {
            **metadata,
            "file_id": file_id,
            "content_type": "text",
            "source": "document",
        }
        if slide_number is not None:
            chunk_meta["page_number"] = slide_number  # slide ≡ page

        return {
            "chunk_id": f"{file_id}_text_{idx}",
            "text": text,
            "metadata": chunk_meta,
        }

    def _build_typed_chunk(
        self,
        file_id: str,
        content_type: str,  # "table" | "list"
        idx: int,
        text: str,
        metadata: Dict[str, Any],
        slide_number: int | None,
    ) -> Dict[str, Any]:
        chunk_meta = {
            **metadata,
            "file_id": file_id,
            "content_type": content_type,
            "source": "document",
        }
        if slide_number is not None:
            chunk_meta["page_number"] = slide_number

        return {
            "chunk_id": f"{file_id}_{content_type}_{idx}",
            "text": text,
            "metadata": chunk_meta,
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
        chunk_meta = {
            **metadata,
            "file_id": file_id,
            "content_type": "image",
            "source": "document",
            "page_number": image.get("page_number"),  # slide number
        }

        return {
            "chunk_id": f"{file_id}_image_{idx}",
            "text": "",  # intentionally empty — embed via image bytes
            "image": {
                "image_id": image.get("image_id"),
                "image_bytes": image.get("image_bytes"),
            },
            "metadata": chunk_meta,
        }
