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

Implementation context:

Project uses a modular service structure under app/services/.
Place tagging under: app/services/tagging/tagging_service.py

Chunk shape coming in (from chunking layer):

Text/transcript chunk:
{
    "chunk_id": "<file_id>_text_<idx>",
    "text": "...",
    "metadata": {
        "file_id": "...",
        "content_type": "text",        # or "table", "list"
        "source": "document",          # or "transcript"
        "course_code": "...",
        "year": "...",
        ...
    }
}

Image chunk:
{
    "chunk_id": "<file_id>_image_<idx>",
    "image": {
        "image_id": "...",
        "image_bytes": "..."
    },
    "metadata": {
        "file_id": "...",
        "content_type": "image",
        "source": "document",
        "page_number": ...,
        "course_code": "...",
        "year": "..."
    }
}

Detection rules:
- Image chunk: "image" key is present, "text" key is absent
- Transcript chunk: metadata["source"] == "transcript"
- All other chunks with "text" key → tag normally

Output shape (must include image key for Stage 5 embedding):
{
    "chunk_id": "...",
    "text": "...",        # empty string "" for image chunks
    "image": {...},       # None for text/transcript chunks
    "metadata": {...},    # preserved exactly, never modified
    "tags": {
        "subject": "...",
        "topic": "...",
        "keywords": [...],
        "difficulty": "..."
    }
}

Config:
- GROQ_API_KEY and GROQ_MODEL = "llama-3.1-8b-instant" are available via app/core/config.py settings object
- Do not hardcode API keys

Error handling:
- If Groq call fails, return empty tags (do not crash the pipeline)
- Log failures with chunk_id