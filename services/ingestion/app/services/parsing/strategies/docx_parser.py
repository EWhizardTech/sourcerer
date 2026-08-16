# app/services/parsing/strategies/docx_parser.py

import base64
import logging
import re
import zipfile
from io import BytesIO
from typing import Any, Dict, List, Tuple

from app.services.parsing.base import BaseParser

logger = logging.getLogger(__name__)

# Heading styles recognised by python-docx (case-insensitive prefix match)
_HEADING_STYLE_PREFIXES = ("heading", "title", "subtitle")

# Relationship type for hyperlinks inside DOCX XML
_HYPERLINK_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
)


class DOCXParser(BaseParser):
    """
    DOCX parser (.docx).

    Primary:  python-docx  – structured extraction preserving headings,
                              paragraphs, tables, lists, and embedded images.
    Fallback: zipfile + raw XML – plain-text extraction when python-docx
                                   cannot open the file (corrupt / legacy).

    Output shape mirrors PDFParser / PPTParser exactly:
    {
        "text":             str,
        "sections":         [...],
        "tables":           [...],
        "lists":            [...],
        "images":           [...],
        "external_content": [...],
        "metadata":         {...},
    }
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def parse(self, content: bytes, file_name: str) -> Dict[str, Any]:
        docx_error: str | None = None

        # ---- primary path ------------------------------------------------
        try:
            result = self._parse_with_docx(content, file_name)

            if result["text"].strip():
                logger.info(
                    "Parsed DOCX %s via python-docx: %d sections, %d tables, %d images",
                    file_name,
                    len(result["sections"]),
                    len(result["tables"]),
                    len(result["images"]),
                )
                return result

            docx_error = "python-docx returned empty text"
            logger.warning(
                "python-docx returned empty text for %s, using XML fallback",
                file_name,
            )

        except Exception as exc:
            docx_error = str(exc)
            logger.warning(
                "python-docx parsing failed for %s, using XML fallback: %s",
                file_name,
                exc,
            )

        # ---- fallback path -----------------------------------------------
        try:
            text, sections = self._parse_with_xml_fallback(content)
            logger.info(
                "Parsed DOCX %s via XML fallback: %d sections",
                file_name,
                len(sections),
            )
            return self._build_result(
                text=text,
                sections=sections,
                tables=[],
                lists=[],
                images=[],
                metadata={
                    "parser": "docx",
                    "file_name": file_name,
                    "extraction_backend": "xml_fallback",
                    "docx_error": docx_error,
                },
            )

        except Exception as fallback_exc:
            logger.exception(
                "DOCX parsing failed for %s in both primary and fallback: %s",
                file_name,
                fallback_exc,
            )
            return self._build_result(
                text="",
                sections=[],
                tables=[],
                lists=[],
                images=[],
                metadata={
                    "parser": "docx",
                    "file_name": file_name,
                    "error": str(fallback_exc),
                    "docx_error": docx_error,
                },
            )

    # ------------------------------------------------------------------ #
    # Primary: python-docx
    # ------------------------------------------------------------------ #

    def _parse_with_docx(self, content: bytes, file_name: str) -> Dict[str, Any]:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(BytesIO(content))

        all_text_parts: List[str] = []
        sections: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        lists_: List[Dict[str, Any]] = []
        images: List[Dict[str, Any]] = []

        # Image extraction requires the relationship map from the document part
        image_rels = self._collect_image_rels(doc)

        current_heading: str | None = None
        current_paragraphs: List[str] = []
        current_bullets: List[str] = []
        para_index = 0

        def _flush_section():
            """Commit buffered paragraphs + bullets as one section."""
            nonlocal current_heading, current_paragraphs, current_bullets

            content_text = "\n".join(current_paragraphs).strip()
            if current_bullets:
                lists_.append(
                    {
                        "type": "list",
                        "content": "\n".join(current_bullets),
                    }
                )

            if current_heading or content_text:
                sections.append(
                    {
                        "type": "section",
                        "heading": current_heading,
                        "content": content_text,
                    }
                )
                all_text_parts.append(
                    "\n".join(filter(None, [current_heading, content_text]))
                )

            current_heading = None
            current_paragraphs = []
            current_bullets = []

        for block in doc.element.body:
            tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

            # ---- TABLE ---------------------------------------------------
            if tag == "tbl":
                _flush_section()
                from docx.table import Table as DocxTable

                tbl = DocxTable(block, doc)
                md_table = self._table_to_markdown(tbl)
                if md_table:
                    tables.append({"type": "table", "content": md_table})
                    all_text_parts.append(md_table)
                continue

            # ---- PARAGRAPH -----------------------------------------------
            if tag == "p":
                from docx.text.paragraph import Paragraph

                para = Paragraph(block, doc)
                text = para.text.strip()

                style_name = (para.style.name or "").lower()
                is_heading = any(
                    style_name.startswith(p) for p in _HEADING_STYLE_PREFIXES
                )
                is_list_item = "list" in style_name

                # Extract any inline images in this paragraph
                for img_entry in self._extract_inline_images(
                    block, image_rels, para_index
                ):
                    images.append(img_entry)

                if is_heading:
                    _flush_section()
                    current_heading = text
                    para_index += 1
                    continue

                if not text:
                    para_index += 1
                    continue

                if is_list_item:
                    bullet = re.sub(r"^[•\-–●*]\s*", "", text)
                    current_bullets.append(f"- {bullet}")
                else:
                    if current_bullets:
                        lists_.append(
                            {
                                "type": "list",
                                "content": "\n".join(current_bullets),
                            }
                        )
                        current_bullets = []
                    current_paragraphs.append(text)

                para_index += 1

        _flush_section()

        text = "\n\n".join(all_text_parts).strip()

        # Collect hyperlinks → external_content (YouTube links handled upstream)
        external_links = self._collect_hyperlinks(doc)

        return self._build_result(
            text=text,
            sections=sections,
            tables=tables,
            lists=lists_,
            images=images,
            metadata={
                "parser": "docx",
                "file_name": file_name,
                "extraction_backend": "python-docx",
                "total_paragraphs": para_index,
            },
            external_content=external_links,
        )

    # ------------------------------------------------------------------ #
    # Fallback: zipfile + raw XML
    # ------------------------------------------------------------------ #

    def _parse_with_xml_fallback(
        self, content: bytes
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        .docx files are ZIP archives. The body lives at word/document.xml.
        Strip XML tags to recover readable text. No structure is preserved.
        """
        with zipfile.ZipFile(BytesIO(content)) as zf:
            if "word/document.xml" not in zf.namelist():
                raise ValueError("word/document.xml not found in archive")

            xml_bytes = zf.read("word/document.xml")
            raw = xml_bytes.decode("utf-8", errors="ignore")

        text = self._strip_xml_tags(raw)

        # Split into pseudo-sections on double newlines
        chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
        sections = [
            {"type": "section", "heading": None, "content": chunk} for chunk in chunks
        ]

        return "\n\n".join(chunks), sections

    # ------------------------------------------------------------------ #
    # Image helpers
    # ------------------------------------------------------------------ #

    def _collect_image_rels(self, doc) -> Dict[str, bytes]:
        """
        Builds a map of { rId → image_bytes } from the document part's
        relationship table. Only image relationships are included.
        """
        image_rels: Dict[str, bytes] = {}

        try:
            part = doc.part
            for rel in part.rels.values():
                if "image" in rel.reltype:
                    try:
                        image_rels[rel.rId] = rel.target_part.blob
                    except Exception as exc:
                        logger.debug("Could not read image rel %s: %s", rel.rId, exc)
        except Exception as exc:
            logger.debug("Could not collect image rels: %s", exc)

        return image_rels

    def _extract_inline_images(
        self,
        para_element,
        image_rels: Dict[str, bytes],
        para_index: int,
    ) -> List[Dict[str, Any]]:
        """
        Scans a paragraph XML element for <a:blip r:embed="rId..."/> references
        and returns normalised image entries for each one found.
        """
        extracted: List[Dict[str, Any]] = []

        # Namespace-aware search for drawing blips
        NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
        NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

        for blip in para_element.iter(f"{{{NS_A}}}blip"):
            r_embed = blip.get(f"{{{NS_R}}}embed")
            if not r_embed or r_embed not in image_rels:
                continue

            blob = image_rels[r_embed]
            ext = self._guess_ext(blob)
            image_id = f"para{para_index}_{r_embed}.{ext}"

            extracted.append(
                {
                    "image_id": image_id,
                    "image_bytes": base64.b64encode(blob).decode("utf-8"),
                    "page_number": None,  # DOCX has no page-level concept
                    "content_type": f"image/{ext}",
                }
            )

        return extracted

    @staticmethod
    def _guess_ext(blob: bytes) -> str:
        """Infer image extension from magic bytes."""
        if blob[:4] == b"\x89PNG":
            return "png"
        if blob[:2] == b"\xff\xd8":
            return "jpg"
        if blob[:4] == b"GIF8":
            return "gif"
        if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
            return "webp"
        return "png"  # safe default

    # ------------------------------------------------------------------ #
    # Table helper
    # ------------------------------------------------------------------ #

    @staticmethod
    def _table_to_markdown(table) -> str:
        """Converts a python-docx Table to a Markdown-style grid string."""
        rows: List[List[str]] = []

        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            rows.append(cells)

        if not rows:
            return ""

        col_count = max(len(r) for r in rows)
        # Pad rows that have fewer cells (merged cells scenario)
        rows = [r + [""] * (col_count - len(r)) for r in rows]

        col_widths = [
            max(len(rows[r][c]) for r in range(len(rows))) for c in range(col_count)
        ]

        def fmt_row(cells: List[str]) -> str:
            return (
                "| " + " | ".join(c.ljust(w) for c, w in zip(cells, col_widths)) + " |"
            )

        separator = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"

        lines = [fmt_row(rows[0]), separator]
        for row in rows[1:]:
            lines.append(fmt_row(row))

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Hyperlink helper
    # ------------------------------------------------------------------ #

    @staticmethod
    def _collect_hyperlinks(doc) -> List[str]:
        """Returns all external hyperlink URLs found in the document."""
        urls: List[str] = []
        try:
            for rel in doc.part.rels.values():
                if rel.reltype == _HYPERLINK_REL_TYPE and rel.is_external:
                    url = str(rel._target)
                    if url:
                        urls.append(url)
        except Exception as exc:
            logger.debug("Could not collect hyperlinks: %s", exc)
        return urls

    # ------------------------------------------------------------------ #
    # Misc helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _strip_xml_tags(xml: str) -> str:
        text = re.sub(r"<[^>]+>", " ", xml)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _build_result(
        text: str,
        sections: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        lists: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        external_content: List[str] | None = None,
    ) -> Dict[str, Any]:
        return {
            "text": text,
            "sections": sections,
            "tables": tables,
            "lists": lists,
            "images": images,
            "external_content": external_content or [],
            "metadata": metadata,
        }
