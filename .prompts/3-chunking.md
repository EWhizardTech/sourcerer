Implement chunking module.

Input:
Parsed output + folder metadata + file_id

Requirements:

1. Chunk document text
2. Chunk transcripts separately
3. Each image becomes its own chunk:

{
  "chunk_id": "...",
  "image": {
    "image_id": "...",
    "image_bytes": "..."
  },
  "metadata": {
    "file_id": "...",
    "source": "document",
    "content_type": "image",
    "page_number": ...,
    "course_code": "...",
    "year": "..."
  }
}

4. Deterministic chunk_id:
<file_id>_<content_type>_<index>

Constraints:
- Do NOT mix image with text
- Keep all streams separate

At the end:
- Show example including image chunk