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