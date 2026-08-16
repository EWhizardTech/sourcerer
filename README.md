# Sourcerer

AI-powered RAG platform for educational content — microservice backend behind an API gateway, with a Next.js frontend.

- **Streaming chat** over your course material with memory, hybrid search, reranking, and inline citations
- **Quiz generation** — MCQs built from retrieved content (T5 + spaCy/NLTK)
- **Google Drive ingestion** — parse → chunk → tag → embed → index (Celery + Qdrant)

## Quickstart

```bash
cp .env.schema .env            # fill in Qdrant / Groq / Gemini keys
docker compose up -d --build

# UI       → http://localhost:3000
# Gateway  → http://localhost:8001/health
```

## Layout

```
frontend/              Next.js app (Tailwind v4, streaming chat UI)
services/
  gateway/             API gateway — proxy, SSE passthrough, health aggregation
  ingestion/           Drive intake + processing pipeline + Celery worker
  retrieval/           Agentic RAG chat (LangGraph, SSE, Redis memory)
  quiz/                MCQ generation
libs/sourcerer-core/   Shared config, embeddings, vector store, retrieval
docs/                  MkDocs documentation
```

## Documentation

Full docs (architecture, RAG pipeline, per-service reference, deployment, development):

```bash
uv sync --all-packages
uv run mkdocs serve            # http://localhost:8000
```

## Development

```bash
uv sync --all-packages                     # Python workspace
cd frontend && npm install && npm run dev  # UI on :3000
```

See `docs/development.md` for running services individually and testing.
