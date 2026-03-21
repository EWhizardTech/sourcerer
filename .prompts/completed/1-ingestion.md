Implement ONLY the Google Drive ingestion module.

Requirements:
- Connect to Google Drive using service account or OAuth
- Fetch files from a specific folder (folder_id will be provided)
- Support:
  - PDF
  - TXT
  - DOCX
  - PPT
  - MD (markdown)

Return:
[
  {
    "file_id": "...",
    "file_name": "...",
    "mime_type": "...",
    "file_path": "...",   // full folder path
    "modified_time": "...", 
    "content": bytes
  }
]


Also:
- Include function to download file content locally or in memory
- Do NOT implement parsing, chunking, or embeddings yet
- Ensure file_id is stable across runs


Structure:
- services/gdrive_service.py
- routes/ingestion.py

Add:
- FastAPI endpoint: /ingest/gdrive
- Accept folder_id as input

Keep it minimal but working.

At the end:
- Show how to test with sample request