import logging
from typing import Any, Dict

from app.services.parsing.base import BaseParser

logger = logging.getLogger(__name__)


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
        try:
            from docling.document_converter import DocumentConverter
            import tempfile
            from pathlib import Path

            converter = DocumentConverter()
            # result = converter.convert(content)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            result = converter.convert(tmp_path)

            doc = result.document

            text = doc.export_to_text()

            sections = []
            tables = []
            images = []
            lists = []

            for element in doc.elements:
                el_type = element.__class__.__name__.lower()

                if "heading" in el_type:
                    sections.append(
                        {
                            "type": "section",
                            "heading": element.text,
                            "content": "",
                            "page": getattr(element, "page_number", None),
                        }
                    )

                elif "paragraph" in el_type:
                    if sections:
                        sections[-1]["content"] += "\n" + element.text
                    else:
                        sections.append(
                            {
                                "type": "section",
                                "heading": None,
                                "content": element.text,
                                "page": getattr(element, "page_number", None),
                            }
                        )

                elif "table" in el_type:
                    tables.append(
                        {
                            "type": "table",
                            "content": element.export_to_markdown(),
                            "page": getattr(element, "page_number", None),
                        }
                    )

                elif "picture" in el_type:
                    images.append(
                        {
                            "type": "image",
                            "caption": getattr(element, "caption", ""),
                            "page": getattr(element, "page_number", None),
                        }
                    )

                elif "list" in el_type:
                    lists.append(
                        {
                            "type": "list",
                            "content": element.export_to_markdown(),
                            "page": getattr(element, "page_number", None),
                        }
                    )

            logger.info(f"Parsed PDF {file_name}: {len(sections)} sections, {len(tables)} tables")

            return {
                "text": text,
                "sections": sections,
                "tables": tables,
                "images": images,
                "lists": lists,
                "external_content": [],
                "metadata": {
                    "parser": "pdf",
                    "file_name": file_name,
                },
            }

        except Exception as exc:
            logger.exception("PDF parsing failed for %s: %s", file_name, exc)

            return {
                "text": "",
                "sections": [],
                "tables": [],
                "images": [],
                "lists": [],
                "external_content": [],
                "metadata": {
                    "parser": "pdf",
                    "error": str(exc),
                },
            }