# app/services/chunking/factory.py

import logging
from typing import Type

from app.services.chunking.base import BaseChunker
from app.services.chunking.strategies.fixed_window_chunker import \
    FixedWindowChunker
from app.services.chunking.strategies.pdf_chunker import PDFChunker
from app.services.chunking.strategies.section_chunker import SectionChunker

logger = logging.getLogger(__name__)


class ChunkerFactory:
    """
    Factory for selecting chunking strategies.

    Design principles:
    - Explicit over implicit
    - Safe fallback
    - Easy extensibility
    """

    _registry: dict[str, Type[BaseChunker]] = {
        "fixed": FixedWindowChunker,
        "section": SectionChunker,
        "pdf": PDFChunker,
    }

    _default_strategy = "fixed"

    @classmethod
    def get_chunker(cls, strategy: str | None = None, **kwargs) -> BaseChunker:
        """
        Returns a chunker instance.

        Args:
            strategy: chunking strategy name
            kwargs: passed to chunker constructor

        Returns:
            BaseChunker instance
        """

        if strategy is None:
            strategy = cls._default_strategy

        chunker_cls = cls._registry.get(strategy)

        if not chunker_cls:
            logger.warning(
                "Unknown chunking strategy '%s'. Falling back to '%s'.",
                strategy,
                cls._default_strategy,
            )
            chunker_cls = cls._registry[cls._default_strategy]

        logger.debug("Using chunker: %s", chunker_cls.__name__)

        return chunker_cls(**kwargs)
