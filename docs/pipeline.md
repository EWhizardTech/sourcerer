# Sourcerer Pipeline

## Current processing flow

1. A user submits a Google Drive folder ID through the Streamlit ingestion page.
2. The frontend calls `POST /ingest/gdrive` on the FastAPI backend.
3. The backend recursively downloads supported files from Google Drive.
4. Folder metadata is extracted from the breadcrumb-style file path and merged with optional course/year inputs.
5. Each file is queued to Celery for background processing.
6. The worker computes a content hash and checks the SQLite tracking table.
7. If the file is unchanged, processing stops early with `SKIP`.
8. If the file changed, existing vectors for that `file_id` are removed from Qdrant before reprocessing.
9. The file is parsed using a MIME-based parser factory.
10. The parsed document is chunked using an automatically selected strategy.
11. Each chunk is tagged with Groq unless it is an image chunk.
12. Tagged chunks are embedded with Gemini Embeddings 2.
13. Embedded chunks are upserted into Qdrant.
14. The tracking store is updated only after the entire pipeline completes successfully.

## Stage details

### 1. Google Drive ingestion

The Drive helper in [app/services/gdrive_service.py](../app/services/gdrive_service.py) authenticates with a service account, walks the folder tree recursively, exports Google Docs and Slides when necessary, and returns file records with raw bytes.

### 2. Folder metadata extraction

[app/services/metadata_service.py](../app/services/metadata_service.py) derives tags from the folder breadcrumb. The route can also carry explicit `course_code`, `year`, and `include_root_as_tag` inputs.

### 3. Incremental check

[app/services/incremental_service.py](../app/services/incremental_service.py) computes an MD5 hash for the raw file bytes and compares it against SQLite state. The worker branches on `NEW`, `SKIP`, or `UPDATE`.

### 4. Parsing

[app/services/parsing/factory.py](../app/services/parsing/factory.py) chooses the parser by MIME type. The parser implementations live under `app/services/parsing/strategies/`.

### 5. Chunking

[app/services/chunking/chunker.py](../app/services/chunking/chunker.py) chooses the chunking strategy from the parsed document shape. Chunk IDs are deterministic UUIDv5 values derived from file ID plus chunk index and type.

### 6. Tagging

[app/services/tagging/tagging_service.py](../app/services/tagging/tagging_service.py) calls Groq with a strict JSON schema. It returns `subject`, `topic`, `keywords`, and `difficulty`. Image chunks skip tagging and keep empty tags.

### 7. Embedding

[app/services/embedding/embedding_service.py](../app/services/embedding/embedding_service.py) produces dense vectors sized to `QDRANT_VECTOR_SIZE`. Text chunks are embedded with a tag-aware description plus text. Image chunks are embedded only if their decoded bytes stay below the configured size limit.

### 8. Vector storage

[app/services/vector_store/vector_store_service.py](../app/services/vector_store/vector_store_service.py) upserts into Qdrant with dense vectors and optional sparse vectors. Payloads include file metadata and tag fields for retrieval-time filtering.

### 9. Tracking update

The final write to SQLite happens after Qdrant storage succeeds. This is the main guardrail that prevents a file from being marked processed before the pipeline actually finished.

## Failure behavior

- Drive download failures skip the bad file and continue the folder walk.
- Tagging falls back to empty tags after retries are exhausted.
- Embedding skips chunks that cannot be embedded.
- `UPDATE` removes existing vectors first so re-ingestion does not duplicate stale chunks.
- Tracking is not updated if processing fails before the final step.

## Useful implementation notes

- `file_id` is the stable identity across runs.
- Qdrant collection creation is idempotent.
- The pipeline is designed to be resumable at the file level, not only at the folder level.
- Current retrieval UI is only a placeholder.
