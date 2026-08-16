# Development

## Prerequisites

- Python 3.13 + [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Docker (for Redis, or the full stack)

## Workspace setup

The Python side is a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/): one lockfile, one `.venv`, members under `libs/` and `services/`.

```bash
uv sync --all-packages        # install every service's deps + sourcerer-core (editable)
```

!!! note
    On Windows this resolves CUDA (cu128) torch wheels; Linux containers get CPU wheels. Both come from the same `uv.lock`.

## Running services locally

Each service runs from its own directory (the local `app/` package resolves from the CWD):

```bash
docker compose up -d redis                      # broker + chat memory

# Gateway (points at local service ports)
cd services/gateway
INGESTION_URL=http://localhost:8010 RETRIEVAL_URL=http://localhost:8011 QUIZ_URL=http://localhost:8012 \
  uv run uvicorn app.main:app --port 8001

cd services/ingestion && uv run uvicorn app.main:app --port 8010
cd services/retrieval && uv run uvicorn app.main:app --port 8011
cd services/quiz      && uv run uvicorn app.main:app --port 8012

# Celery worker
cd services/ingestion && uv run celery -A app.workers.celery_app.celery worker --loglevel=info

# Frontend
cd frontend && npm run dev
```

## Tests

Tests live next to each package and run from that package's directory:

```bash
cd libs/sourcerer-core   && uv run python -m pytest tests -q
cd services/ingestion    && uv run python -m pytest tests -q
cd services/retrieval    && uv run python -m pytest tests -q
cd services/quiz         && uv run python -m pytest tests -q
```

!!! warning "Known pre-existing failures"
    `test_incremental_service.py` (collection error), one gdrive mock test, one quiz
    validation assertion, and the live-Qdrant vector-store test predate the
    microservice split and are unrelated to it.

## Documentation

```bash
uv run mkdocs serve       # http://localhost:8000
```

## Conventions

- Shared code goes in `libs/sourcerer-core` — services never import each other.
- New service deps go in that service's `pyproject.toml`; re-lock with `uv lock`.
- Docker images must stay CPU-only; GPU belongs in `docker-compose.gpu.yml` overrides.
