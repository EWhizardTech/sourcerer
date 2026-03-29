import base64
import logging

from app.services.chunking.chunker import chunk_document
from app.services.parsing.factory import ParserFactory
from app.workers.celery_app import celery


@celery.task(name="process_file_task")
def process_file_task(file_id, file_name, mime_type, file_bytes, metadata):
    content = base64.b64decode(file_bytes)

    # STEP 1 — Parsing
    parser = ParserFactory.get_parser(mime_type)
    parsed_doc = parser.parse(content, file_name)

    # STEP 2 — Chunking
    chunks = chunk_document(parsed_doc, metadata, file_id)

    logging.info(f"Processed file {file_id} into {len(chunks)} chunks.")

    # Step 3 — Store chunks in the Qdrant database (this is a placeholder, implement as needed)

    return {"file_id": file_id, "chunks": len(chunks)}
