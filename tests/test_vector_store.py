import json
import uuid
from typing import List

from app.services.vector_store.vector_store_service import VectorStoreService
from app.services.embedding.embedding_types import EmbeddedChunk


def get_mock_text_chunk(chunk_id: str = "chunk_1") -> EmbeddedChunk:
    return {
        "chunk_id": chunk_id,
        "dense_vector": [0.1] * 2048,
        "text": "This is a sample text chunk for Sourcerer.",
        "image": None,
        "metadata": {
            "file_id": "file_abc_123",
            "content_type": "text",
            "source": "document",
            "course_code": "CS101",
            "year": "2024",
            "page_number": 1,
            "exam_type": "midterm"
        },
        "tags": {
            "subject": "Computer Science",
            "topic": "Intro",
            "keywords": ["python", "code"],
            "difficulty": "Easy"
        }
    }


def get_mock_image_chunk(chunk_id: str = "chunk_img_1") -> EmbeddedChunk:
    return {
        "chunk_id": chunk_id,
        "dense_vector": [0.5] * 2048,
        "text": "Description of image", # often image chunks have some text from OCR or tags
        "image": {
            "image_id": "img_123",
            "image_bytes": "..."
        },
        "metadata": {
            "file_id": "file_abc_123",
            "content_type": "image",
            "source": "document",
            "course_code": "CS101",
            "year": "2024",
            "page_number": 2
        },
        "tags": {
            "subject": "Computer Science",
            "topic": "Hardware",
            "keywords": ["cpu", "ram"],
            "difficulty": "Medium"
        }
    }


def test_vector_store():
    print("--- 1. Initializing VectorStoreService ---")
    service = VectorStoreService()
    
    # Normally we'd call service.create_collection() but that requires a live Qdrant
    print("\n--- 2. Example Stored Point (Text Chunk) ---")
    text_chunk = get_mock_text_chunk()
    
    # Simulate internal processing for display
    vectors_text = {
        "dense": text_chunk["dense_vector"][:5] + ["..."],
        "sparse": f"models.Document(text='{text_chunk['text']}', model='Qdrant/bm25')"
    }
    print(f"ID: {text_chunk['chunk_id']}")
    print(f"Vectors: {json.dumps(vectors_text, indent=2)}")
    print(f"Payload Sample: {json.dumps(text_chunk['metadata'], indent=2)}")

    print("\n--- 3. Example Stored Point (Image Chunk) ---")
    image_chunk = get_mock_image_chunk()
    vectors_img = {
        "dense": image_chunk["dense_vector"][:5] + ["..."],
        "sparse": "OMITTED (image chunk)"
    }
    print(f"ID: {image_chunk['chunk_id']}")
    print(f"Vectors: {json.dumps(vectors_img, indent=2)}")

    print("\n--- 4. Verification logic for upsert_chunks ---")
    # This just shows we can handle the list
    service.upsert_chunks([text_chunk, image_chunk])
    print("Logic passed (Mocked for display)...")

if __name__ == "__main__":
    # We can't actually run this against Qdrant without credentials, 
    # but we can show the structure.
    test_vector_store()
