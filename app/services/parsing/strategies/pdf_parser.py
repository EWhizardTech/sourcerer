import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.services.parsing.base import BaseParser

logger = logging.getLogger(__name__)


_converter = None
_converter_device = None


def _resolve_docling_device() -> str:
    """Resolves Docling accelerator device with GPU-first fallback behavior."""
    requested = os.getenv("DOCLING_ACCELERATOR_DEVICE", "auto").strip().lower()
    allowed = {"auto", "cpu", "cuda", "mps", "xpu"}

    if requested not in allowed:
        logger.warning(
            "Invalid DOCLING_ACCELERATOR_DEVICE=%s, falling back to auto", requested
        )
        requested = "auto"

    if requested != "auto":
        return requested

    # Prefer CUDA when available, otherwise force CPU.
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception as exc:
        logger.debug("CUDA detection via torch failed, using CPU fallback: %s", exc)

    return "cpu"


def _build_converter(device: str):
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pdf_options = PdfPipelineOptions(
        accelerator_options=AcceleratorOptions(device=device)
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
        }
    )


def _get_converter():
    global _converter, _converter_device
    device = _resolve_docling_device()

    # Rebuild only if first use or device preference changed.
    if _converter is None or _converter_device != device:
        _converter = _build_converter(device)
        _converter_device = device
        logger.info("Initialized Docling converter with accelerator=%s", device)

    return _converter


class PDFParser(BaseParser):
    """
    PDF parser using Docling.

    Extracts:
    - text
    - sections (headings)
    - tables
    - images
    - lists
    """

    def parse(self, content: bytes, file_name: str) -> Dict[str, Any]:
        docling_error = None

        try:
            text, sections, tables, lists_ = self._parse_with_docling(content)

            if text.strip():
                logger.info(
                    "Parsed PDF %s via docling: %d sections, %d tables",
                    file_name,
                    len(sections),
                    len(tables),
                )
                return self._build_result(
                    text=text,
                    sections=sections,
                    tables=tables,
                    lists=lists_,
                    metadata={
                        "parser": "pdf",
                        "file_name": file_name,
                        "extraction_backend": "docling",
                    },
                )

            docling_error = "Docling returned empty text"
            logger.warning(
                "Docling returned empty text for %s, using PyMuPDF fallback", file_name
            )
        except Exception as exc:
            docling_error = str(exc)
            logger.warning(
                "Docling parsing failed for %s, using PyMuPDF fallback: %s",
                file_name,
                exc,
            )

        try:
            text, sections = self._parse_with_pymupdf(content)
            logger.info(
                "Parsed PDF %s via pymupdf fallback: %d sections",
                file_name,
                len(sections),
            )
            return self._build_result(
                text=text,
                sections=sections,
                tables=[],
                lists=[],
                metadata={
                    "parser": "pdf",
                    "file_name": file_name,
                    "extraction_backend": "pymupdf",
                    "docling_error": docling_error,
                },
            )
        except Exception as fallback_exc:
            logger.exception(
                "PDF parsing failed for %s in docling and fallback parser: %s",
                file_name,
                fallback_exc,
            )
            return self._build_result(
                text="",
                sections=[],
                tables=[],
                lists=[],
                metadata={
                    "parser": "pdf",
                    "file_name": file_name,
                    "error": str(fallback_exc),
                    "docling_error": docling_error,
                },
            )

    def _extract_from_markdown(
        self, markdown: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        sections: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        lists_: List[Dict[str, Any]] = []

        current_heading: str | None = None
        current_lines: List[str] = []

        in_table = False
        table_lines: List[str] = []

        current_list: List[str] = []

        for raw_line in markdown.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()

            # ---------- TABLE DETECTION ----------
            if "|" in line and re.match(r"\|.+\|", line):
                in_table = True
                table_lines.append(line)
                continue

            if in_table:
                tables.append(
                    {
                        "type": "table",
                        "content": "\n".join(table_lines),
                    }
                )
                table_lines = []
                in_table = False

            # ---------- LIST DETECTION ----------
            if stripped.startswith("- ") or re.match(r"^\d+\.\s+", stripped):
                current_list.append(stripped)
                continue
            else:
                if current_list:
                    lists_.append(
                        {
                            "type": "list",
                            "content": "\n".join(current_list),
                        }
                    )
                    current_list = []

            # ---------- HEADING DETECTION ----------
            if re.match(r"^#{1,6}\s+", line):
                if current_heading is not None or current_lines:
                    sections.append(
                        {
                            "type": "section",
                            "heading": current_heading,
                            "content": "\n".join(current_lines).strip(),
                        }
                    )

                current_heading = re.sub(r"^#{1,6}\s+", "", line).strip()
                current_lines = []
                continue

            # ---------- NORMAL TEXT ----------
            current_lines.append(line)

        # ---------- FINAL FLUSH ----------
        if in_table and table_lines:
            tables.append(
                {
                    "type": "table",
                    "content": "\n".join(table_lines),
                }
            )

        if current_list:
            lists_.append(
                {
                    "type": "list",
                    "content": "\n".join(current_list),
                }
            )

        if current_heading is not None or current_lines:
            sections.append(
                {
                    "type": "section",
                    "heading": current_heading,
                    "content": "\n".join(current_lines).strip(),
                }
            )

        # Clean empty sections
        sections = [
            s
            for s in sections
            if (s.get("content") and s["content"].strip()) or s.get("heading")
        ]

        return sections, tables, lists_

    def _parse_with_pymupdf(self, content: bytes) -> Tuple[str, List[Dict[str, Any]]]:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=content, filetype="pdf")
        page_texts: List[str] = []

        try:
            for page_index, page in enumerate(doc, start=1):
                page_text = page.get_text("text") or ""
                cleaned = page_text.strip()

                if cleaned:
                    page_texts.append(cleaned)

            text = "\n\n".join(page_texts).strip()
            sections = self._sections_from_plain_text(text)

            return text, sections

        finally:
            doc.close()

    def _parse_with_docling(
        self, content: bytes
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

        tmp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            converter = _get_converter()  # singleton
            result = converter.convert(tmp_path)
            doc = result.document

            text = doc.export_to_text() if hasattr(doc, "export_to_text") else ""
            markdown = (
                doc.export_to_markdown() if hasattr(doc, "export_to_markdown") else ""
            )

            sections, tables, lists_ = self._extract_from_markdown(markdown)

            if not sections and text.strip():
                sections = self._sections_from_plain_text(text)

            return text, sections, tables, lists_

        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    logger.debug("Could not remove temp PDF file: %s", tmp_path)

    def _sections_from_plain_text(self, text: str) -> List[Dict[str, Any]]:
        chunks = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        return [
            {
                "type": "section",
                "heading": None,
                "content": chunk,
            }
            for chunk in chunks
        ]

    def _build_result(
        self,
        text: str,
        sections: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        lists: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "text": text,
            "sections": sections,
            "tables": tables,
            "images": [],
            "lists": lists,
            "external_content": [],
            "metadata": metadata,
        }
