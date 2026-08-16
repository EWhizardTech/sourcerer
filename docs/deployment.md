# Deployment

The whole stack runs with Docker Compose.

```bash
cp .env.schema .env       # fill in credentials
docker compose up -d --build
```

## Services & ports

| Compose service | Runtime image | Published |
|---|---|---|
| `frontend` | node:22-alpine (standalone Next.js) | **3000** |
| `gateway` | python:3.13-slim | **8001** |
| `ingestion` / `ingestion-worker` | python:3.13-slim (+docling/torch-cpu) — one shared image | — |
| `retrieval` | python:3.13-slim | — |
| `quiz` | python:3.13-slim (+transformers/torch-cpu) | — |
| `redis` | redis:latest | 6380 (host convenience) |

Only the frontend and gateway are published; services talk over the compose network.

## Image strategy

Each service has its own **multi-stage** Dockerfile building from the repo root.

**Builder stage** (`ghcr.io/astral-sh/uv:python3.13-bookworm-slim`):

1. Copy workspace manifests (`pyproject.toml`, `uv.lock`, member pyprojects) — cached layer
2. `uv sync --frozen --no-dev --package <service> --no-install-workspace` — third-party deps only
3. Copy `libs/` + the service's source
4. Final `uv sync --frozen --no-dev --package <service>` installs `sourcerer-core`

**Runtime stage** (`python:3.13-slim-bookworm`, the same base the uv image derives from) copies only `/srv/.venv`, `/srv/libs` (`sourcerer-core` is installed editable from there), and the service source — uv and intermediate build layers never ship.

`ingestion-worker` has no `build:` of its own; it reuses the `sourcerer-ingestion` image and only overrides the command, so the heaviest image builds once.

Containers get **CPU torch wheels** (small); CUDA never enters an image. For GPU workers see `docker-compose.gpu.yml`.

!!! note "Build context hygiene"
    `.dockerignore` excludes `**/.cache/` and `**/.venv/` at any depth. Local dev
    runs drop multi-GB model caches inside `services/*/.cache`; if those leak into
    the build context, every build re-transfers gigabytes and bakes models into
    the images. A no-change `docker compose build` should take seconds — if it
    takes minutes, check `transferring context` in the build output.

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
