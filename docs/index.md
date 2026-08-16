# Sourcerer

**Sourcerer** is an AI-powered Retrieval-Augmented Generation (RAG) platform for educational content. It ingests course material from Google Drive, indexes it with hybrid vector search, and serves:

- **Streaming chat** with conversation memory and grounded, inline-cited answers
- **Quiz generation** — multiple-choice questions built from retrieved content
- **A modern web UI** (Next.js) over a microservice backend behind a single API gateway

## At a glance

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), Tailwind CSS v4, framer-motion |
| Gateway | FastAPI + httpx streaming reverse proxy |
| Retrieval | LangGraph agent, Groq LLMs, SSE streaming, Redis memory |
| Search | Qdrant hybrid (dense Gemini embeddings + BM25 sparse, RRF fusion), cross-encoder reranking |
| Ingestion | Google Drive → Docling parsing → chunking → LLM tagging → embedding, via Celery |
| Quiz | T5 question generation + spaCy/NLTK distractor mining |

## Quickstart

```bash
# 1. Configure environment
cp .env.schema .env   # fill in API keys (Qdrant, Groq, Gemini, ...)

# 2. Run the full stack
docker compose up -d --build

# 3. Open the app
#    UI:       http://localhost:3000
#    Gateway:  http://localhost:8001/health
```

For local development without Docker, see [Development](development.md).

## Repository layout

```
sourcerer/
├── frontend/              # Next.js web app
├── services/
│   ├── gateway/           # API gateway (reverse proxy + aggregate health)
│   ├── ingestion/         # Drive intake + processing pipeline + Celery worker
│   ├── retrieval/         # Agentic RAG chat service
│   └── quiz/              # MCQ generation service
├── libs/sourcerer-core/   # Shared: config, embedding, vector store, retrieval
├── docs/                  # This documentation (MkDocs)
└── docker-compose.yml
```
