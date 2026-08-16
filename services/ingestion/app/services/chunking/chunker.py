# app/services/chunking/chunker.py

import logging

from app.services.chunking.factory import ChunkerFactory

logger = logging.getLogger(__name__)


def chunk_document(parsed_doc, metadata, file_id):
    """
    Automatically selects chunking strategy based on document structure.
    """

    parser_type = parsed_doc.get("metadata", {}).get("parser")

    if parser_type == "pdf":
        strategy = "pdf"
    elif parser_type == "ppt":
        strategy = "ppt"
    elif parser_type == "docx":
        strategy = "docx"
    elif parsed_doc.get("sections"):
        strategy = "section"
    else:
        strategy = "fixed"

    logger.debug("Using %s chunking strategy for file_id=%s", strategy, file_id)

    chunker = ChunkerFactory.get_chunker(strategy)

    return chunker.chunk(parsed_doc, metadata, file_id)
