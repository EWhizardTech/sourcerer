Implement vector storage for hybrid search using Qdrant.

Input:
Chunks with:
- dense_vector (Gemini)
- sparse_vector (BM25) [optional for images]
- metadata
- tags

Requirements:

1. Use chunk_id as Qdrant point ID

2. Store MULTIPLE NAMED VECTORS:

{
  "id": chunk_id,
  "vector": {
    "dense": [...],     // REQUIRED

    "sparse": {         // REQUIRED for text/transcript
      "indices": [...],
      "values": [...]
    }
  },
  "payload": {...}
}

3. Payload MUST include:

{
  "text": "...",

  // REQUIRED FOR INCREMENTAL
  "file_id": "...",

  // Manual metadata
  "course_code": "...",
  "year": "...",
  "exam_type": "...",

  // LLM tags
  "subject": "...",
  "topic": "...",
  "keywords": [...],
  "difficulty": "...",

  // Content info
  "content_type": "...",
  "source": "...",

  // Optional
  "video_id": "...",
  "parent_doc": "...",
  "page_number": ...
}

4. Special handling:

- For IMAGE chunks:
  - store ONLY dense vector
  - omit sparse vector

5. Collection MUST be created with:

- dense vector config
- sparse vector config

6. Upsert behavior:

- inserting same chunk_id MUST overwrite existing point
- must be idempotent

Structure:
- services/vector_store.py

Functions:
- create_collection()
- upsert_chunks()

Constraints:

- MUST use named vectors ("dense", "sparse")
- MUST support hybrid search
- DO NOT flatten vectors into one
- DO NOT lose metadata

At the end:

- Show example stored point (text chunk)
- Show example stored point (image chunk)
- Show overwrite example

Implementation context:

Place vector store under: app/services/vector_store/vector_store_service.py

IMPORTANT - Sparse vector generation:
Do NOT implement a separate sparse embedding service.
Qdrant generates BM25 sparse vectors internally via FastEmbed.
When upserting, pass text as models.Document(text=..., model="Qdrant/bm25")
for the sparse named vector. Qdrant handles the rest server-side.

Dependencies:
- qdrant-client (with fastembed extra): pip install qdrant-client[fastembed]
- QDRANT_URL and QDRANT_COLLECTION_NAME available via app/core/config.py settings object

Chunk shape coming in (from embedding layer, Stage 5):
{
    "chunk_id": "...",
    "dense_vector": [...],        # float list from Gemini
    "text": "...",                # empty string "" for image chunks
    "image": {                    # None for text/transcript chunks
        "image_id": "...",
        "image_bytes": "..."
    },
    "metadata": {
        "file_id": "...",
        "content_type": "text",   # or "image", "table", "list"
        "source": "document",     # or "transcript"
        "course_code": "...",
        "year": "...",
        "page_number": ...        # optional
    },
    "tags": {
        "subject": "...",
        "topic": "...",
        "keywords": [...],
        "difficulty": "..."
    }
}

Collection creation (create_collection):
- Must configure BOTH dense and sparse named vectors
- Dense: cosine similarity, size must match Gemini embedding-002 output (768)
- Sparse: use IDF modifier for proper BM25 scoring

Collection config:
    from qdrant_client import QdrantClient, models

    client.create_collection(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=768,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                modifier=models.Modifier.IDF
            )
        },
    )

- create_collection() must be idempotent:
  check if collection exists first, skip creation if it does

Upsert logic (upsert_chunks):

For TEXT and TRANSCRIPT chunks (content_type != "image"):
    - Store dense_vector under named vector "dense"
    - Store text as models.Document(text=chunk["text"], model="Qdrant/bm25")
      under named vector "sparse" — Qdrant generates BM25 internally
    - point id = chunk_id (use as string)

    vector={
        "dense": chunk["dense_vector"],
        "sparse": models.Document(
            text=chunk["text"],
            model="Qdrant/bm25",
        ),
    }

For IMAGE chunks (content_type == "image"):
    - Store ONLY dense_vector under named vector "dense"
    - Omit sparse vector entirely (no text to index)

    vector={
        "dense": chunk["dense_vector"],
    }

Payload (same structure for all chunk types):
    {
        "text": chunk["text"],
        "file_id": chunk["metadata"]["file_id"],
        "course_code": chunk["metadata"].get("course_code", ""),
        "year": chunk["metadata"].get("year", ""),
        "content_type": chunk["metadata"]["content_type"],
        "source": chunk["metadata"]["source"],
        "page_number": chunk["metadata"].get("page_number"),
        "subject": chunk["tags"]["subject"],
        "topic": chunk["tags"]["topic"],
        "keywords": chunk["tags"]["keywords"],
        "difficulty": chunk["tags"]["difficulty"],
    }

Upsert behavior:
- Use client.upsert() with upsert=True (default) — same chunk_id overwrites existing point
- Must be idempotent — reinserting same chunk_id is safe
- Batch upsert all chunks in a single call

Config to add in app/core/config.py:
- QDRANT_URL: str (e.g. "http://localhost:6333")
- QDRANT_COLLECTION_NAME: str (e.g. "sourcerer")

Error handling:
- If upsert fails, log error with chunk_ids and raise
- If collection already exists on create_collection(), log and continue