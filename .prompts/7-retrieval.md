Implement ONLY retrieval.

Input:
{
  "query": "...",
  "filters": {
    "course_code": "...",
    "year": "...",
    "exam_type": "...",
    "content_type": "...",
    "subject": "..."
  }
}

Flow:

1. Embed query
2. Apply metadata filters
3. Vector search (Qdrant)
4. Return top_k

Output:
[
  {
    "text": "...",
    "score": ...,
    "metadata": {...},
    "tags": {...}
  }
]

Structure:
- services/retrieval_service.py
- routes/retrieval.py

Constraints:
- Support doc + transcript retrieval
- Filters optional

At the end:
- Show example query + response