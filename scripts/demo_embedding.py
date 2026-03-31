# scripts/demo_embedding.py

import os
import base64
import json
import logging
from app.core.config import settings
from app.services.embedding.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_demo():
    # 1. Check for API configuration
    if not settings.gcp_project_id:
        logger.error("GCP_PROJECT_ID not found in settings!")
        print("\n[ERROR] GCP_PROJECT_ID is missing. Please set it in your .env file or environment.")
        return

    # 2. Prepare sample chunks
    # We'll use the image generated in the previous step
    image_path = "/home/ajayh/.gemini/antigravity/brain/0db13ebd-3e98-413a-9c14-70836da91d0a/sample_embedding_image_1774971422730.png"
    
    image_chunk = None
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            
        image_chunk = {
            "chunk_id": "demo-multimodal-chunk",
            "text": "Diagram showing the internal architecture of the Sourcerer RAG pipeline.",
            "image": {
                "image_bytes": img_b64
            },
            "metadata": {
                "file_id": "file-123",
                "content_type": "image",
                "source": "document"
            },
            "tags": {
                "subject": "System Design",
                "topic": "RAG Architecture",
                "keywords": ["Diagram", "Flow", "Pipeline"],
                "difficulty": "Medium"
            }
        }
        logger.info(f"Loaded demo image from {image_path}")

    text_chunk = {
        "chunk_id": "demo-text-chunk",
        "text": "In a RAG system, the embedding stage transforms both text and metadata into high-dimensional vectors to enable semantic search.",
        "image": None,
        "metadata": {
            "file_id": "file-124",
            "content_type": "text",
            "source": "document"
        },
        "tags": {
            "subject": "Machine Learning",
            "topic": "Vector Embeddings",
            "keywords": ["Dense Vector", "Search", "Semantics"],
            "difficulty": "Easy"
        }
    }

    chunks = [text_chunk]
    if image_chunk:
        chunks.append(image_chunk)

    # 3. Run embedding
    try:
        service = EmbeddingService()
        logger.info(f"Using Vertex AI Project: {settings.gcp_project_id}")
        logger.info(f"Generating embeddings using {service.model_name}...")
        
        results = service.embed_chunks(chunks)
        
        # 4. Show results
        print("\n" + "="*60)
        print("VERTEX AI - GEMINI EMBEDDINGS 2 PREVIEW RESULTS (3072-dim)")
        print("="*60)
        
        for res in results:
            content_type = "MULTIMODAL (Text+Image)" if res.get('image') and res.get('text') else ("IMAGE" if res.get('image') else "TEXT ONLY")
            print(f"\n[Chunk ID: {res['chunk_id']}]")
            print(f"Type: {content_type}")
            print(f"Vector Length: {len(res['dense_vector'])}")
            print(f"First 5 values: {[round(v, 4) for v in res['dense_vector'][:5]]}")
            
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")

if __name__ == "__main__":
    run_demo()
