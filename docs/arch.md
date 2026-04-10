# Sourcerer Backend — System Architecture

## Overview

Sourcerer is a production-grade AI RAG (Retrieval-Augmented Generation) backend for educational content. It ingests documents from **Google Drive**, processes them through a multi-stage pipeline, and serves an **agentic LLM-powered retrieval API**.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          SOURCERER BACKEND                           │
│                                                                      │
│  ┌─────────────────────┐          ┌──────────────────────────────┐  │
│  │   INGESTION PATH    │          │       RETRIEVAL PATH         │  │
│  │                     │          │                              │  │
│  │  Google Drive       │          │  Client App / User           │  │
│  │       ↓             │          │        ↓                     │  │
│  │  FastAPI            │          │  POST /api/v1/retrieve/      │  │
│  │  POST /ingest/gdrive│          │        ↓                     │  │
│  │       ↓             │          │  LangGraph ReAct Agent       │  │
│  │  Celery Queue       │          │   (llama-3.1-8b via Groq)   │  │
│  │  (Redis broker)     │          │        ↓                     │  │
│  │       ↓             │          │  search_documents tool       │  │
│  │  process_file_task  │          │        ↓                     │  │
│  │  (8-stage pipeline) │          │  Gemini embed_query          │  │
│  │       ↓             │          │        ↓                     │  │
│  │  Qdrant Vector DB   │←─────────│  Qdrant Hybrid Search (RRF)  │  │
│  └─────────────────────┘          └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Ingestion Pipeline (8 Stages)

```
POST /api/v1/ingest/gdrive
         │
         ▼
┌─────────────────────────┐
│  Stage 1: GDrive        │  gdrive_service.py
│  Ingestion              │  • Auth via service account
│                         │  • Recursive folder traversal
│  Output: List[FileRecord]│  • Downloads file bytes in-memory
└──────────┬──────────────┘  • Builds breadcrumb file_path
           │
           ▼ (Celery task dispatched per file)
┌─────────────────────────┐
│  Stage 2: Incremental   │  incremental_service.py
│  Check                  │  • MD5 hash of file content
│                         │  • Checks SQLite file_tracking table
│  → NEW: proceed         │  • NEW → proceed to stage 3
│  → SKIP: stop           │  • SKIP → return immediately
│  → UPDATE: delete+proc  │  • UPDATE → delete Qdrant vectors first
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 3: Metadata      │  metadata_service.py
│  Extraction             │  • Extracts course_code, year from
│                         │    folder path breadcrumbs
│  Output: metadata dict  │  • Passes metadata to all chunks
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 4: Parsing       │  parsing/factory.py
│                         │  ParserFactory.get_parser(mime_type)
│  Supported formats:     │  • PDF → pdf_parser.py (PyMuPDF)
│  • PDF                  │  • DOCX → docx_parser.py (Docling)
│  • DOCX                 │  • PPTX → ppt_parser.py (Docling)
│  • PPTX/PPT             │  • TXT → text_parser.py
│  • TXT/Markdown         │  • MD → markdown_parser.py
│                         │
│  Output: ParsedDocument │  Produces text blocks + image blocks
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 5: Chunking      │  chunking/chunker.py → strategies/
│                         │  chunk_document(parsed_doc, metadata, file_id)
│  Strategies:            │  • pdf_chunker.py
│  • PDF layout-aware     │  • docx_chunker.py
│  • DOCX section-based   │  • ppt_chunker.py
│  • PPT slide-based      │  • section_chunker.py
│  • Fixed window fallback│  • fixed_window_chunker.py
│                         │
│  Chunk IDs: DETERMINISTIC│  Hash-based IDs — stable across re-runs
│  Output: List[Chunk]    │  Separates TextChunk and ImageChunk
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 6: Tagging       │  tagging/tagging_service.py
│  (LLM-based)            │  • Groq API: llama-3.1-8b-instant
│                         │  • Multi-key round-robin (comma-sep keys)
│  Tags per chunk:        │  • 429 → cycle all keys → 10s wait → retry
│  • subject              │  • Images: empty tags (no LLM call)
│  • topic                │  • Strict JSON schema via Groq
│  • keywords[]           │
│  • difficulty           │
│  Output: List[TaggedChunk]
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 7: Embedding     │  embedding/embedding_service.py
│                         │  • Model: gemini-embedding-2-preview
│  Text chunks:           │  • Text: "{description}\n\n{text}"
│  • description + text   │  • Image: description + raw bytes (multimodal)
│  Image chunks:          │  • Output dim: 2048 (QDRANT_VECTOR_SIZE)
│  • description + pixels │  • Query: task_type=RETRIEVAL_QUERY
│  Output: List[EmbeddedChunk] (dense_vector added)
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 8: Qdrant Storage│  vector_store/vector_store_service.py
│                         │  • Named vector: "dense" (list[float])
│  Hybrid storage:        │  • Named vector: "sparse" (BM25 Document)
│  • dense vector         │  • Images: dense only (no sparse)
│  • sparse BM25 vector   │  • Payload: full metadata + tags
│  (images: dense only)   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 9: Tracking      │  incremental_service.update_tracking_record()
│  Update                 │  • SQLite: INSERT OR REPLACE
│                         │  • Only called on SUCCESS
│  SQLite record:         │  • Guards against re-processing unchanged files
│  • file_id (PK)         │
│  • file_hash (MD5)      │
│  • last_processed_at    │
└─────────────────────────┘
```

---

## Retrieval Pipeline

```
POST /api/v1/retrieve/
  { "query": "What is a binary search tree?" }
         │
         ▼
┌──────────────────────────────────────────────────┐
│             LangGraph StateGraph                 │
│                                                  │
│  State: MessagesState (list of messages)         │
│                                                  │
│  START ──→ [ agent_node ]                        │
│                  │                               │
│         llm_with_tools.invoke(                   │
│           [SystemMessage] + messages)            │
│                  │                               │
│         ┌────────┴─────────┐                     │
│         │                  │                     │
│   [tool_call?]        [no tool_call]             │
│         │                  │                     │
│         ▼                  ▼                     │
│   [ ToolNode ]          [ END ]                  │
│         │                                        │
│  search_documents(                               │
│    query, k, subject?,                           │
│    topic?, keywords?, difficulty?)               │
│         │                                        │
│    embed_query(query)   ← Gemini API             │
│         │                                        │
│    vector_store.search(                          │
│      dense_vector, query_text, k, filters)       │
│         │                                        │
│    Qdrant: Prefetch dense + sparse               │
│    Fusion: RRF                                   │
│         │                                        │
│    format string of doc chunks                   │
│         │                                        │
│   back to [ agent_node ] ───┘                    │
│                                                  │
│  recursion_limit=10 (safety cap)                 │
└──────────────────────────────────────────────────┘
         │
         ▼
  { "answer": "..." }
```

---

## Qdrant Collection Schema

```
Collection: sourcerer_collection
├── vectors_config:
│   └── "dense": VectorParams(size=2048, distance=Cosine)
└── sparse_vectors_config:
    └── "sparse": SparseVectorParams(modifier=IDF)

Point Payload:
{
  "text":          string,
  "file_id":       string,       ← Google Drive fileId (stable)
  "course_code":   string,
  "year":          string,
  "content_type":  "text" | "image" | "transcript",
  "source":        string,       ← breadcrumb path
  "page_number":   int | null,
  "subject":       string,       ← LLM tag
  "topic":         string,       ← LLM tag
  "keywords":      list[string], ← LLM tag
  "difficulty":    "Easy" | "Medium" | "Hard",
  "exam_type":     string,       ← optional
  "video_id":      string,       ← optional (YouTube)
  "parent_doc":    string        ← optional
}
```

---

## Component Dependency Graph

```
app/main.py
├── routes/ingestion.py
│   ├── services/gdrive_service.py
│   ├── services/metadata_service.py
│   └── workers/tasks.py (Celery)
│       ├── services/incremental_service.py ──→ SQLite + Qdrant
│       ├── services/parsing/factory.py ──→ strategies/
│       ├── services/chunking/chunker.py ──→ strategies/
│       ├── services/tagging/tagging_service.py ──→ Groq API
│       ├── services/embedding/embedding_service.py ──→ Gemini API
│       └── services/vector_store/vector_store_service.py ──→ Qdrant
│
└── routes/retrieval.py
    └── services/retrieval/graph.py (LangGraph)
        ├── services/retrieval/tools.py
        │   ├── services/embedding/embedding_service.py
        │   └── services/vector_store/vector_store_service.py
        └── langchain_groq.ChatGroq (llama-3.1-8b-instant)
```

---

## Infrastructure

| Component        | Tech                                | Notes                              |
|-----------------|-------------------------------------|------------------------------------|
| API Server      | FastAPI + Uvicorn                    | `uv run uvicorn app.main:app`      |
| Task Queue      | Celery 5.x                          | Async per-file processing          |
| Broker/Backend  | Redis (port 6380)                   | docker-compose.infra.yml           |
| Vector DB       | Qdrant                              | Cloud or local Docker              |
| Tracking DB     | SQLite                              | `data/sourcerer.db` (auto-created) |
| Embeddings      | Gemini embedding-2-preview (Google)  | 2048-dim, multimodal               |
| LLM (Tagging)   | llama-3.1-8b-instant (Groq)          | JSON-mode, strict schema           |
| LLM (Retrieval) | llama-3.1-8b-instant (Groq)          | Tool-binding via LangChain         |
| Drive Auth      | GCP Service Account                  | `secrets/*.json`                   |

---

## What's Not Yet Built

| Feature            | Status  | Reference                     |
|--------------------|---------|-------------------------------|
| Reranking          | Planned | `.prompts/8-rerank.md`        |
| YouTube Transcripts| Schema ready | `video_id` payload field |
| Auth on API        | Not built | N/A                        |
| course_code filter in retrieval | Partial | tool ignores it |
| Frontend           | Streamlit stub | `/frontend/`          |
