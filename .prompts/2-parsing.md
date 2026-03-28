Now implement the parsing layer.

Input:
- File content from ingestion module

Requirements:

- Extract clean text from:
  - PDF (PyMuPDF or pdfplumber)
  - TXT
  - MD
  - PPT
  - DOCX

- Preserve structure:
  - headings
  - paragraphs


- For PDFs:
  - extract embedded images
  - store:
    {
      "image_id": "...",
      "image_bytes": "...",
      "page_number": ...
    }

- Detect YouTube links
- Extract transcript

Output format:
{
  "text": "...",
  "images": [
    {
      "image_id": "...",
      "image_bytes": "...",
      "page_number": ...
    }
  ],
  "external_content": [...],
  "metadata": {...}
}

Constraints:
- Do NOT chunk
- Do NOT embed

Functions:
- parse_document()
- extract_youtube_links()
- get_youtube_transcript()

At the end:
- Show example output with images