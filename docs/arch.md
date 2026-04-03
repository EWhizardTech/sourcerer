# Sourcerer Architecture

## Overview

Sourcerer is an AI-powered RAG backend built around a simple ingestion-to-retrieval pipeline. The current implementation is centered on Google Drive ingestion, background processing with Celery, and vector storage in Qdrant. A Streamlit frontend provides a lightweight admin UI for ingestion and a placeholder retrieval page.

## Runtime layout

The backend exposes a FastAPI app from [app/main.py](../app/main.py). It registers the ingestion router from [app/routes/ingestion.py](../app/routes/ingestion.py) and exposes a `/health` probe. Logging is configured at startup with standard Python logging.

The worker runtime lives in [app/workers/celery_app.py](../app/workers/celery_app.py) and [app/workers/tasks.py](../app/workers/tasks.py). Celery uses Redis as broker/backing transport, while task results are intentionally ignored because pipeline progress is tracked in SQLite and Qdrant.

The frontend is a Streamlit app in [frontend/app.py](../frontend/app.py) with supporting API and styling helpers in [frontend/components/api.py](../frontend/components/api.py) and [frontend/components/styling.py](../frontend/components/styling.py).

## Backend layers

### Ingestion

[app/services/gdrive_service.py](../app/services/gdrive_service.py) authenticates with Google Drive using a service account, walks folder trees recursively, exports Google Docs/Slides where needed, and returns in-memory file payloads. The ingestion route wraps this and returns base64-encoded content to the client while also enqueuing async processing.

### Incremental control

[app/services/incremental_service.py](../app/services/incremental_service.py) owns the SQLite tracking store and Qdrant collection bootstrap. It computes a file hash, decides whether a file is `NEW`, `SKIP`, or `UPDATE`, deletes stale vectors for updates, and writes the tracking record only after successful processing.

### Parsing and chunking

Parser selection is centralized in [app/services/parsing/factory.py](../app/services/parsing/factory.py). Chunk strategy selection is centralized in [app/services/chunking/factory.py](../app/services/chunking/factory.py) and [app/services/chunking/chunker.py](../app/services/chunking/chunker.py). The typed data contracts for parsed content, text chunks, and image chunks are defined in [app/services/chunking/types.py](../app/services/chunking/types.py).

The pipeline currently supports text, markdown, PDF, DOCX, and PowerPoint inputs through strategy-based parser and chunker implementations under `app/services/parsing/strategies/` and `app/services/chunking/strategies/`.

### Tagging

[app/services/tagging/tagging_service.py](../app/services/tagging/tagging_service.py) uses Groq with a strict JSON schema to produce subject/topic/keyword/difficulty tags for text chunks. Image chunks bypass LLM tagging and receive empty tags, which keeps the schema stable for downstream steps.

### Embedding

[app/services/embedding/embedding_service.py](../app/services/embedding/embedding_service.py) uses Gemini Embeddings 2 through `google-genai` to create dense vectors. For text chunks it combines a short tag-derived description with the chunk text. For image chunks it can embed image bytes directly when the payload is small enough.

### Vector storage

[app/services/vector_store/vector_store_service.py](../app/services/vector_store/vector_store_service.py) writes hybrid Qdrant points with a dense vector and optional sparse text vector. Payloads include file metadata plus the generated tag fields so retrieval can filter and rank by document structure and content meaning.

## Frontend layout

`frontend/app.py` is the landing page. It performs a backend health check and introduces the current feature set. The Streamlit multipage app exposes [frontend/pages/1_ingestion.py](../frontend/pages/1_ingestion.py) for starting Google Drive ingestion and [frontend/pages/2_retrieval.py](../frontend/pages/2_retrieval.py) as a disabled placeholder for later search UI.

The frontend makes synchronous HTTP requests to the backend through [frontend/components/api.py](../frontend/components/api.py). Styling is centralized in [frontend/components/styling.py](../frontend/components/styling.py).

## Key boundaries

- FastAPI handles request validation and queueing.
- Celery handles heavy document processing.
- SQLite stores file tracking state.
- Qdrant stores vectors and payloads.
- Groq handles tagging.
- Gemini handles embeddings.

## What to change carefully

If you add a new file type, update Google Drive support, parser selection, chunking behavior, and tests together. If you change the vector shape or Qdrant payload, update the embedding and vector store layers in the same pass. If you change tracking semantics, keep the tracking write at the end of the worker pipeline.

## Files to inspect first when resuming work

- [app/main.py](../app/main.py)
- [app/routes/ingestion.py](../app/routes/ingestion.py)
- [app/workers/tasks.py](../app/workers/tasks.py)
- [app/services/incremental_service.py](../app/services/incremental_service.py)
- [app/services/vector_store/vector_store_service.py](../app/services/vector_store/vector_store_service.py)
- [frontend/app.py](../frontend/app.py)
- [frontend/pages/1_ingestion.py](../frontend/pages/1_ingestion.py)
