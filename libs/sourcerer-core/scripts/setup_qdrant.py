# setup_qdrant.py
import logging
from qdrant_client import QdrantClient, models
from sourcerer_core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_collection():
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    collection_name = settings.QDRANT_COLLECTION_NAME

    # 1. Delete existing collection to clear bad schema
    if client.collection_exists(collection_name):
        logger.info(f"Deleting existing collection '{collection_name}'...")
        client.delete_collection(collection_name)

    # 2. Create collection with named vectors for Hybrid Search
    logger.info(f"Creating collection '{collection_name}' with named vectors...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": models.VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                modifier=models.Modifier.IDF
            )
        },
    )

    # 3. Verify Schema
    info = client.get_collection(collection_name)
    logger.info(f"Collection '{collection_name}' created successfully.")
    
    # Check dense vectors
    dense_config = info.config.params.vectors
    if isinstance(dense_config, dict) and "dense" in dense_config:
        logger.info("✅ SUCCESS: 'dense' vector found.")
    else:
        logger.error("❌ FAILURE: 'dense' vector missing or wrongly configured.")
        
    # Check sparse vectors
    sparse_config = info.config.params.sparse_vectors
    if sparse_config and "sparse" in sparse_config:
        logger.info("✅ SUCCESS: 'sparse' vector found.")
    else:
        logger.error("❌ FAILURE: 'sparse' vector missing.")

if __name__ == "__main__":
    setup_collection()
