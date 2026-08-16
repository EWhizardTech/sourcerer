# test_qdrant_fix.py
import uuid
import logging
from app.services.chunking.strategies.pdf_chunker import PDFChunker
from sourcerer_core.vector_store.vector_store_service import vector_store_service
from sourcerer_core.embedding.embedding_types import EmbeddedChunk

logging.basicConfig(level=logging.INFO)

def test_chunk_id_uuid():
    chunker = PDFChunker()
    file_id = "test_file_id"
    metadata = {"source": "test", "content_type": "text"}
    parsed_doc = {"sections": [{"heading": "Header", "content": "Sample content"}]}
    
    chunks = chunker.chunk(parsed_doc, metadata, file_id)
    
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        print(f"Generated Chunk ID: {chunk_id}")
        # Verify it's a valid UUID
        try:
            uuid.UUID(chunk_id)
            print("Verified: UUID is valid.")
        except ValueError:
            print("FAILED: UUID is not valid.")
            return False
            
    return True

if __name__ == "__main__":
    if test_chunk_id_uuid():
        print("\nFix Verified: Chunk IDs are now valid UUIDs.")
    else:
        print("\nFix Failed: Chunk IDs are still strings.")
