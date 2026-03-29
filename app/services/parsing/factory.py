# app/services/parsing/factory.py

import logging

from app.services.parsing.strategies.markdown_parser import MarkdownParser
from app.services.parsing.strategies.text_parser import TextParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Centralized parser resolver.

    Easy to extend without touching business logic.
    """

    _registry = {
        "text/plain": TextParser,
        "text/csv": TextParser,
        "text/markdown": MarkdownParser,
    }

    @classmethod
    def get_parser(cls, mime_type: str):
        parser_cls = cls._registry.get(mime_type, TextParser)

        logger.debug(
            "Selected parser %s for mime_type=%s", parser_cls.__name__, mime_type
        )

        return parser_cls()
