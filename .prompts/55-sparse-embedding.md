Implement sparse embedding.

Input:
Chunks (text + transcript only)

Requirements:

1. Generate sparse vectors using BM25

2. Output:

[
  {
    "chunk_id": "...",
    "sparse_vector": {
      "indices": [...],
      "values": [...]
    }
  }
]

3. Skip image chunks

Structure:
- services/sparse_embedding_service.py

Constraints:
- deterministic
- text only

At the end:
- Show example sparse vector