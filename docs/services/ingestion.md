# Ingestion Service

`services/ingestion` — Google Drive intake plus the asynchronous processing pipeline.

## Endpoints

### `POST /api/v1/ingest/gdrive`

```json
{
  "folder_id": "1AbC…",
  "course_code": "20XW81",
  "year": "2026",
  "include_root_as_tag": false
}
```

Recursively lists the folder, downloads supported files (PDF, DOCX, PPTX, TXT, MD), extracts breadcrumb metadata, and dispatches **one Celery task per file**. Responds immediately with the queued file list — processing happens in the worker.

## Worker pipeline (per file)

1. **Incremental check** — MD5 hash against the SQLite tracking DB: `NEW` → process, `SKIP` → stop, `UPDATE` → delete old vectors, reprocess
2. **Parse** — Docling for rich formats, with image extraction
3. **Chunk** — strategy per format (`pdf_chunker`, `docx_chunker`, `ppt_chunker`, `section_chunker`, `fixed_window_chunker`)
4. **Tag** — Groq LLM labels each chunk: subject, topic, keywords, difficulty
5. **Embed** — Gemini multimodal embeddings (2048-dim), text + image chunks
6. **Store** — Qdrant upsert with dense + BM25 sparse vectors and full metadata payload
7. **Track** — record file hash for future incremental runs

## Running the worker

```bash
# In Docker this is the `ingestion-worker` compose service.
cd services/ingestion
uv run celery -A app.workers.celery_app.celery worker --loglevel=info
```

## Requirements

- `secrets/acc.json` — Google service account with read access to the Drive folder (mounted read-only in Docker)
- Redis (broker + result backend)
- Qdrant + Gemini + Groq credentials in `.env`
