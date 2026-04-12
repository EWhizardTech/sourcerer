# Sourcerer Backend — Project Context

## What is Sourcerer?

Sourcerer is a **production-grade RAG (Retrieval-Augmented Generation) backend** for educational institutions. It allows learners and educators to ask natural language questions against a curated knowledge base of course materials, and receive answers grounded entirely in those documents.

Think of it as a **"smart search + answer engine"** over organized Google Drive folders full of PDFs, slides, and notes.

---

## Domain Context

### Who is the user?
- **Students** asking questions like *"Explain merge sort with examples"* or *"What did the lecture on mitosis cover?"*
- **Educators** who want to expose structured course content as a queryable knowledge base
- **Course administrators** who manage content by organizing Google Drive folders by course and year

### What types of content does it handle?
- PDF lecture notes and textbooks
- DOCX study guides and assignments
- PPTX / PPT slide decks
- Markdown and plain text files
- Google Docs and Google Slides (auto-exported to DOCX/PPTX)
- Images embedded in documents (embed multimodally with Gemini)
- YouTube transcripts (schema support present, ingestion not yet wired)

### How is content organized in Google Drive?
```
Drive Root/
└── CS101/
    └── 2024/
        ├── Lecture_01_Intro.pdf
        ├── Assignment_1.docx
        └── Week2/
            └── Slides.pptx
```
The folder hierarchy is used to automatically extract **course code**, **year**, and **tags** via `metadata_service.py`.

---

## Product Goal

> Given a natural language question, Sourcerer must find the most relevant chunks from the knowledge base and synthesize a grounded answer — without hallucinating.

The system is designed to:
1. **Never answer from prior knowledge** — the LLM is explicitly instructed to use only retrieved documents.
2. **Return "Insufficient info"** if no relevant content is found — honesty over hallucination.
3. **Support multimodal content** — diagrams and images embedded in slides/PDFs are also searchable.

---

## Key Design Decisions

### Why LangGraph?
The retrieval is implemented as a **ReAct agent loop** using LangGraph. This allows the agent to:
- Dynamically decide how many times to search
- Retry with refined queries if first results are poor
- Self-evaluate retrieved docs before answering

This is more powerful than a single-shot retrieval call — the agent can iteratively narrow down to a precise answer.

### Why Hybrid Search (Dense + Sparse)?
- **Dense vectors** (Gemini Embeddings 2) capture semantic meaning — good for paraphrase matching
- **Sparse vectors** (BM25 via Qdrant/bm25 fastembed) capture exact keyword matches — good for technical terms, function names, acronyms
- **RRF fusion** (Reciprocal Rank Fusion) combines both rankings without needing manual score weighting

This gives the best of both worlds: semantic understanding + precise keyword matching.

### Why Groq for Tagging?
- Groq provides **ultra-fast inference** (important for tagging many chunks during ingestion)
- `llama-3.1-8b-instant` is fast and cheap for structured JSON extraction
- Multiple Groq API keys rotated in round-robin to handle rate limits across large batches

### Why Celery for Ingestion?
- Ingesting a large folder with hundreds of files is time-consuming
- The HTTP request returns immediately after queuing tasks
- Celery with Redis broker ensures reliable, async per-file processing with retries

### Why Deterministic Chunk IDs?
- If the same file is re-ingested, existing chunks should map to the **same point IDs** in Qdrant
- This prevents duplicate insertions and ensures idempotent updates
- Chunk IDs are hash-based (derived from file_id + position/content)

### Why SQLite for Tracking?
- Lightweight, no external dependency
- File tracking only needs simple key-value lookups (file_id → hash)
- Auto-created at startup, stored in `data/sourcerer.db`

---

## Current State (as of April 2026)

| Feature                | Status       |
|------------------------|--------------|
| GDrive Ingestion       | ✅ Working   |
| Incremental Processing | ✅ Working   |
| PDF Parsing            | ✅ Working   |
| DOCX/PPTX Parsing      | ✅ Working   |
| Chunking               | ✅ Working   |
| LLM Tagging            | ✅ Working   |
| Gemini Embedding       | ✅ Working   |
| Qdrant Hybrid Storage  | ✅ Working   |
| Retrieval API          | ✅ Working   |
| LangGraph Agent        | ✅ Working   |
| Reranking              | 🔲 Planned   |
| YouTube Transcripts    | 🔲 Schema ready |
| API Auth               | 🔲 Not built |
| Frontend (Streamlit)   | 🔲 Stub only |

---

## Conventions Every Agent Must Follow

1. **Package manager**: Always `uv`. Never `pip`. Install with `uv add <package>`, run with `uv run`.
2. **Coding style**: Google Python Style Guide. All public functions need docstrings.
3. **Logging**: Use `logging.getLogger(__name__)` — not `print` (except debug tooling).
4. **Singletons**: Service classes are instantiated once at module level. Import the singleton, not the class.
5. **Error handling**: Never silently swallow errors in pipeline stages. Log and either raise or return a meaningful fallback.
6. **Testing**: Each feature must be independently testable. Add test files in `tests/`.
7. **No config magic**: All environment configuration goes through `app/core/config.py → Settings`.
8. **Tracking store**: Updated ONLY after full successful pipeline. Never before.

---

## Secrets & Auth

- Google Drive and Gemini use a **GCP service account JSON key** stored in `secrets/`
- Path is configured via `GDRIVE_SERVICE_ACCOUNT_PATH` in `.env`
- Groq API key(s) stored in `GROQ_API_KEY` (comma-separated for multiple keys)
- Gemini API key stored in `GEMINI_API_KEY`
- **The `.env` file is gitignored. Never commit secrets.**

---

## How to Run

```bash
# 1. Install dependencies
uv sync

# 2. Start Redis (for Celery)
docker-compose -f docker-compose.infra.yml up -d

# 3. Start Celery worker
uv run celery -A app.workers.celery_app worker --loglevel=info

# 4. Start FastAPI server
uv run uvicorn app.main:app --reload

# 5. (First time) Set up Qdrant collection
uv run python setup_qdrant.py
```

API docs available at: `http://localhost:8000/docs`

---

## Reference Files

| Purpose                            | File                                  |
|------------------------------------|---------------------------------------|
| Coding rules for AI agents         | `AGENTS.md`                           |
| Full KT for incoming agents        | `agent_handover.json`                 |
| System architecture                | `docs/arch.md`                        |
| This context doc                   | `docs/context.md`                     |
| Retrieval module deep-dive         | `docs/retrieval_module.md`            |
| Vector store design notes          | `.prompts/6-vector-store.md`          |
| Retrieval design notes             | `.prompts/7-retrieval.md`             |
| Reranking design notes (planned)   | `.prompts/8-rerank.md`                |
| Environment variable schema        | `.env.schema`                         |
