Now implement the parsing layer.

Input:
- File content from ingestion module

Requirements:
- Extract clean text from:
  - TXT
  - MD
  - PPT
  - DOCX
- Preserve basic structure:
  - headings (if possible)
  - paragraphs
- Detect YouTube links in the text
   - Regex for:
     - youtube.com/watch?v=
     - youtu.be/
- For each YouTube link:
   - Extract video_id
   - Fetch transcript using:
     - youtube-transcript-api (preferred)
- Store transcript separately AND optionally append to main text

Output format:
{
  "text": "...cleaned document text...",
  "external_content": [
    {
      "type": "youtube",
      "url": "...",
      "video_id": "...",
      "transcript": "..."
    }
  ],
  "metadata": {
    "source": "gdrive",
    "file_name": "...",
    "type": "pdf"
  }
}

Structure:
- services/parser_service.py
- services/youtube_service.py

Constraints:
- If transcript is unavailable, fail gracefully (do not break parsing)
- Do NOT implement chunking yet
- Keep it modular

Functions to implement:
- parse_document(file_bytes, mime_type)
- extract_youtube_links(text)
- get_youtube_transcript(video_id)

At the end:
- Show example: input → output
- Show example:
  input text with YouTube link → parsed output with transcript