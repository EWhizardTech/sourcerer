Implement ONLY retrieval.

Input:
{
  "query": "...",
  "filters": {
    "course_code": "...",
    "year": "...",
    "tags": [...],
  }
}

Flow:

2. Use Qdrant Query API (NOT manual scoring)

3. Perform hybrid search using TWO queries:

   - Dense query (named vector: "dense")
   - Sparse query (named vector: "sparse")

4. Use fusion:
   - RRF (Reciprocal Rank Fusion) OR
   - DBSF (Distribution-Based Score Fusion)

5. Apply metadata filters

6. Return top_k results

Output:
[
  {
    "chunk_id": "...",
    "text": "...",
    "score": ...,
    "metadata": {...},
    "tags": {...}
  }
]

Structure:
- services/retrieval_service.py

Constraints:

- DO NOT manually combine scores
- DO NOT use weighted sum (0.7/0.3)
- MUST use Qdrant Query API
- MUST support:
  - document
  - transcript
  - image

At the end:
- Show example hybrid query call