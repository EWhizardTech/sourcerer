Implement vector storage.

Input:
Chunks with embeddings, metadata, and tags

Requirements:

1. Use chunk_id as Qdrant point ID

2. Store vector + payload

Payload MUST include:

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
  "parent_doc": "..."
}

3. Ensure:
- file_id is always present
- payload fields are consistent

4. Upsert behavior:
- inserting same chunk_id should overwrite old vector


Structure:
- services/vector_store.py

Functions:
- create_collection()
- upsert_chunks()

Constraints:
- Do NOT implement retrieval
- Do NOT lose metadata
- No retrieval yet
- Must support overwrite (idempotent inserts)

At the end:
- Show example stored point
- Show how overwrite works