import base64
import logging

from app.services.chunking.chunker import chunk_document
from app.services.parsing.factory import ParserFactory
from app.services.tagging.tagging_service import tag_chunks
from app.services.embedding.embedding_service import EmbeddingService
from app.workers.celery_app import celery


@celery.task(name="process_file_task")
def process_file_task(file_id, file_name, mime_type, file_bytes, metadata):
    content = base64.b64decode(file_bytes)

    # STEP 1 — Parsing
    parser = ParserFactory.get_parser(mime_type)
    parsed_doc = parser.parse(content, file_name)

    # STEP 2 — Chunking (deterministic IDs)
    chunks = chunk_document(parsed_doc, metadata, file_id)
    logging.info(f"Processed file {file_id} into {len(chunks)} chunks.")
    
    # STEP 3 — Tagging (LLM)
    tagged_chunks = tag_chunks(chunks)
    logging.info(f"Processed file {file_id}: {len(chunks)} chunks tagged.")

    # STEP 4 — Embedding (Multimodal)
    embedding_service = EmbeddingService()
    embedded_chunks = embedding_service.embed_chunks(tagged_chunks)
    logging.info(f"Processed file {file_id}: {len(embedded_chunks)} chunks embedded.")

    # Step 5 — Store chunks in the Qdrant database (upcoming Stage 8)

    return {"file_id": file_id, "chunks": len(embedded_chunks)}
