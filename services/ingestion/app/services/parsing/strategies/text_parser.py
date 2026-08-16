# app/services/parsing/strategies/text_parser.py

import logging
from typing import Any, Dict

from app.services.parsing.base import BaseParser
from app.services.parsing.utils.cleaning import (normalize_text,
                                                 split_paragraphs)

logger = logging.getLogger(__name__)


class TextParser(BaseParser):
    """
    Handles:
    - text/plain
    - text/csv (treated as raw text for now)

    Future:
    - CSV → structured parsing
    """

    def parse(self, content: bytes, file_name: str) -> Dict[str, Any]:
        try:
            text = self._safe_decode(content)
            text = normalize_text(text)

            sections = split_paragraphs(text)

            return {
                "text": text,
                "sections": sections,
                "images": [],
                "external_content": [],
                "metadata": {
                    "parser": "text",
                    "file_name": file_name,
                },
            }

        except Exception as exc:
            logger.exception("Failed to parse text file %s: %s", file_name, exc)

            return {
                "text": "",
                "sections": [],
                "images": [],
                "external_content": [],
                "metadata": {
                    "parser": "text",
                    "error": str(exc),
                },
            }
