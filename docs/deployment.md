# Deployment

The whole stack runs with Docker Compose.

```bash
cp .env.schema .env       # fill in credentials
docker compose up -d --build
```

## Services & ports

| Compose service | Image basis | Published |
|---|---|---|
| `frontend` | node:22-alpine (standalone Next.js) | **3000** |
| `gateway` | uv + python3.13 slim | **8001** |
| `ingestion` / `ingestion-worker` | uv + python3.13 slim (+docling/torch-cpu) | — |
| `retrieval` | uv + python3.13 slim | — |
| `quiz` | uv + python3.13 slim (+transformers/torch-cpu) | — |
| `redis` | redis:latest | 6380 (host convenience) |

Only the frontend and gateway are published; services talk over the compose network.

## Image strategy

Each service has its own Dockerfile building from the repo root:

1. Copy workspace manifests (`pyproject.toml`, `uv.lock`, member pyprojects) — cached layer
2. `uv sync --frozen --no-dev --package <service> --no-install-workspace` — third-party deps only
3. Copy `libs/` + the service's source
4. Final `uv sync --frozen --no-dev --package <service>` installs `sourcerer-core`

Containers get **CPU torch wheels** (small); CUDA never enters an image. For GPU workers see `docker-compose.gpu.yml`.

## Volumes

| Mount | Services | Purpose |
|---|---|---|
| `./secrets → /srv/secrets` (ro) | ingestion(+worker) | Google service account |
| `./.cache → /srv/.cache` | ingestion, retrieval, quiz | Shared HF/spaCy/NLTK/fastembed model cache — warm restarts |
| `./data → …/ingestion/data` | ingestion(+worker) | Incremental-tracking SQLite DB |

## Required environment (`.env`)

| Variable | Used by |
|---|---|
| `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME` | retrieval, quiz, worker |
| `GROQ_API_KEY`, `GROQ_MODEL` | retrieval, worker (tagging) |
| `GEMINI_API_KEY` | retrieval, quiz, worker (embeddings) |
| `TAVILY_API_KEY` | retrieval (optional web search) |
| `HF_TOKEN` | quiz (optional, model downloads) |

Redis and cache-path variables are injected by compose; you don't set them for Docker runs.
