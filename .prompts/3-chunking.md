Implement chunking module.

Input:
Parsed output + folder metadata + file_id

Requirements:

1. Chunk document text:
   - 300–500 tokens
   - 50 token overlap

2. Chunk transcripts separately

3. Generate deterministic chunk_id:

FORMAT:
<file_id>_<content_type>_<index>

Examples:
file123_document_0
file123_document_1
file123_youtube_<videoid>_0

4. Merge metadata into each chunk:

Output:
[
  {
    "chunk_id": "...",
    "text": "...",
    "metadata": {
      "file_id": "...",   ← REQUIRED
      "source": "document",
      "content_type": "document",
      "course_code": "...",
      "year": "...",
      "exam_type": "..."
    }
  },
  {
    "chunk_id": "...",
    "text": "...",
    "metadata": {
      "file_id": "...",   ← REQUIRED
      "source": "youtube",
      "content_type": "video_transcript",
      "video_id": "...",
      "parent_doc": "...",
      "course_code": "...",
      "year": "...",
      "exam_type": "..."
    }
  }
]

Structure:
- services/chunking_service.py

Functions:
- chunk_text(text, metadata)
- chunk_parsed_document(parsed_doc)

Constraints:
- Do NOT merge transcript into document text
- Keep both as separate chunk streams
- No tagging or embeddings yet
- chunk_id MUST be deterministic and unique
- file_id MUST be included in metadata


At the end:
- Show example output with IDs