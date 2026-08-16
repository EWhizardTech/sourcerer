# app/services/parsing/strategies/markdown_parser.py

import logging
import re
from typing import Any, Dict

from app.services.parsing.base import BaseParser
from app.services.parsing.utils.cleaning import normalize_text

logger = logging.getLogger(__name__)


class MarkdownParser(BaseParser):
    """
    Handles:
    - text/markdown

    Features:
    - heading extraction
    - Obsidian-style links [[note]]
    """

    def parse(self, content: bytes, file_name: str) -> Dict[str, Any]:
        try:
            text = self._safe_decode(content)
            text = normalize_text(text)

            sections = []
            current = {"type": "section", "heading": None, "content": []}

            for line in text.split("\n"):
                if line.startswith("#"):
                    if current["content"]:
                        sections.append(current)

                    current = {
                        "type": "section",
                        "heading": line.strip(),
                        "content": [],
                    }
                else:
                    current["content"].append(line)

            if current["content"]:
                sections.append(current)

            # Obsidian links
            links = re.findall(r"\[\[(.*?)\]\]", text)

            return {
                "text": text,
                "sections": sections,
                "images": [],
                "external_content": [],
                "metadata": {
                    "parser": "markdown",
                    "file_name": file_name,
                    "obsidian_links": links,
                },
            }

        except Exception as exc:
            logger.exception("Failed to parse markdown file %s: %s", file_name, exc)

            return {
                "text": "",
                "sections": [],
                "images": [],
                "external_content": [],
                "metadata": {
                    "parser": "markdown",
                    "error": str(exc),
                },
            }
