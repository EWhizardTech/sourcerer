import base64
import logging

from app.services.chunking.chunker import chunk_document
from app.services.embedding.embedding_service import EmbeddingService
from app.services.incremental_service import incremental_service
from app.services.parsing.factory import ParserFactory
from app.services.tagging.tagging_service import tag_chunks
from app.services.vector_store.vector_store_service import vector_store_service
from app.workers.celery_app import celery


@celery.task(name="process_file_task")
def process_file_task(file_id, file_name, mime_type, file_bytes, metadata):
    """Full processing pipeline for a single file.

    Stages:
    1. Incremental Check (NEW, SKIP, UPDATE)
    2. Deletion (if UPDATE)
    3. Parsing
    4. Chunking
    5. Tagging
    6. Embedding
    7. Qdrant Storage
    8. Tracking Update
    """
    content = base64.b64decode(file_bytes)

    # 1. Incremental Check (Stage 2)
    file_hash = incremental_service.compute_hash(content)
    status = incremental_service.check_file_status(file_id, file_hash)

    if status == "SKIP":
        logging.info(f"Skipping file {file_id} (hash match: {file_hash})")
        return {"file_id": file_id, "status": "skipped"}

    if status == "UPDATE":
        logging.info(f"Updating file {file_id}. Deleting existing vectors.")
        incremental_service.delete_existing_vectors(file_id)

    # Ensure collection exists before we start heavy processing
    vector_store_service.create_collection()

    # 3. Parsing (Stage 4)
    parser = ParserFactory.get_parser(mime_type)
    parsed_doc = parser.parse(content, file_name)

    # 4. Chunking (Stage 5)
    chunks = chunk_document(parsed_doc, metadata, file_id)
    logging.info(f"Processed file {file_id} into {len(chunks)} chunks.")

    # 5. Tagging (Stage 6)
    tagged_chunks = tag_chunks(chunks)
    logging.info(f"Processed file {file_id}: {len(chunks)} chunks tagged.")

    # 6. Embedding (Stage 7)
    embedding_service = EmbeddingService()
    embedded_chunks = embedding_service.embed_chunks(tagged_chunks)
    logging.info(f"Processed file {file_id}: {len(embedded_chunks)} chunks embedded.")

    # 7. Qdrant Storage (Stage 8)
    vector_store_service.upsert_chunks(embedded_chunks)
    logging.info(f"Stored {len(embedded_chunks)} chunks in Qdrant for file {file_id}.")

    # 8. Tracking Update (Stage 9 - Pipeline Completion)
    incremental_service.update_tracking_record(file_id, file_hash)
    logging.info(f"Completed pipeline for file {file_id}.")

    return {
        "file_id": file_id,
        "status": status.lower(),
        "chunks": len(embedded_chunks),
    }
