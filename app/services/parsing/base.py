# app/services/parsing/base.py

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base parser.

    All parsers MUST:
    - return normalized ParsedDocument
    - never raise fatal exceptions (fail gracefully)
    """

    @abstractmethod
    def parse(self, content: bytes, file_name: str) -> dict:
        pass

    def _safe_decode(self, content: bytes, file_name: str = "unknown") -> str:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "UTF-8 decode failed for %s, falling back to latin-1",
                file_name,
            )
            return content.decode("latin-1", errors="ignore")
