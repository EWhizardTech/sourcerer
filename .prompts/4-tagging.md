Implement ONLY tagging.

Input:
Chunks with metadata

Requirements:

Generate for EACH chunk:
- subject
- topic
- keywords (3–5)
- difficulty

Use llama-3.1-8b-instant by groq with structured output.


If chunk contains image:
   - leave out and make it empty tags


STRICT LLM OUTPUT:
{
  "subject": "...",
  "topic": "...",
  "keywords": [...],
  "difficulty": "..."
}

IMPORTANT:

- Do NOT generate:
  - course_code
  - year
  - exam_type
  - content_type

MERGING:

Final output:
{
  "chunk_id": "...",
  "text": "...",
  "metadata": {...},   // preserved exactly
  "tags": {
    "subject": "...",
    "topic": "...",
    "keywords": [...],
    "difficulty": "..."
  }
}

Rules:
- Never overwrite metadata
- Tag transcript chunks independently

Structure:
- services/tagging_service.py

Functions:
- tag_chunk()
- tag_chunks()

At the end:
- Show:
  - document chunk result
  - transcript chunk result