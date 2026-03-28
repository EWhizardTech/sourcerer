Implement embedding.

Input:
Tagged chunks

Requirements:

1. Use Gemini embedding-2

2. If:
   - text chunk → embed text
   - transcript → embed text
   - image chunk → embed image

OUTPUT: 

[
  {
    "chunk_id": "...",
    "dense_vector": [...],
    "text": "...",
    "image": {...},
    "metadata": {...},
    "tags": {...}
  }
]

Constraints:
- Do NOT embed metadata
- Do NOT mix text + image

IMPORTANT:
- No sparse vectors here

At the end:
- Show text + image embedding example