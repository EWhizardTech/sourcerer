Implement embedding.

Input:
Tagged chunks

Requirements:
- Generate embeddings using Gemini embedding-2
- Use ONLY chunk["text"]

Output:
[
  {
    "chunk_id": "...",
    "embedding": [...],
    "text": "...",
    "metadata": {...},
    "tags": {...}
  }
]

Structure:
- services/embedding_service.py

Constraints:
- No Qdrant yet
- Batch processing

At the end:
- Show example