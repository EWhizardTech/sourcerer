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

Implementation context:

Place embedding under: app/services/embedding/embedding_service.py

Chunk shape coming in (from tagging layer):

Text/transcript chunk:
{
    "chunk_id": "...",
    "text": "...",
    "image": null,
    "metadata": {
        "file_id": "...",
        "content_type": "text",     # or "table", "list"
        "source": "document",       # or "transcript"
        "course_code": "...",
        "year": "..."
    },
    "tags": {
        "subject": "...",
        "topic": "...",
        "keywords": [...],
        "difficulty": "..."
    }
}

Image chunk:
{
    "chunk_id": "...",
    "text": "",
    "image": {
        "image_id": "...",
        "image_bytes": "..."        # raw bytes
    },
    "metadata": {
        "file_id": "...",
        "content_type": "image",
        "source": "document",
        "page_number": ...
    },
    "tags": {
        "subject": "",
        "topic": "",
        "keywords": [],
        "difficulty": ""
    }
}

Detection rules:
- Image chunk: chunk["image"] is not None
- Text/transcript chunk: chunk["image"] is None → embed chunk["text"]

Gemini setup:
- Model: gemini-embedding-002
- GEMINI_API_KEY available via app/core/config.py settings object
- Use google-genai SDK (import google.genai)
- For text: client.models.embed_content(model=..., contents=[...]) — batch all text chunks in one call
- For images: embed one at a time using raw bytes from chunk["image"]["image_bytes"]
- Task type: "RETRIEVAL_DOCUMENT" for text/transcript, "RETRIEVAL_QUERY" is only for queries

Batching strategy:
- Separate chunks into two lists: text_chunks and image_chunks
- Embed ALL text chunks in a single batched API call
- Embed image chunks one at a time (Gemini multimodal does not support image batching)
- Merge results back by chunk_id

Output shape (must preserve all fields, just add dense_vector):
{
    "chunk_id": "...",
    "dense_vector": [...],      # float list from Gemini
    "text": "...",              # preserved from input
    "image": {...},             # preserved from input (None for text)
    "metadata": {...},          # preserved exactly, never modified
    "tags": {...}               # preserved exactly, never modified
}

Error handling:
- If embedding fails for a chunk, log the chunk_id and skip it (do not crash)
- Do not embed metadata or tags
- Do not mix text and image in the same API call

Config to add in app/core/config.py:
- GEMINI_API_KEY: str