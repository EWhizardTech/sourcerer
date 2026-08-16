# Build context: repo root

# --- builder: resolve and install the venv with uv ---
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_LINK_MODE=copy
WORKDIR /srv

# Workspace manifests only — cached until a lockfile/pyproject changes.
COPY pyproject.toml uv.lock ./
COPY libs/sourcerer-core/pyproject.toml libs/sourcerer-core/
COPY services/gateway/pyproject.toml services/gateway/
COPY services/ingestion/pyproject.toml services/ingestion/
COPY services/retrieval/pyproject.toml services/retrieval/
COPY services/quiz/pyproject.toml services/quiz/
COPY services/portal/pyproject.toml services/portal/

# Third-party deps first (cached), then workspace members.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package sourcerer-retrieval --no-install-workspace

COPY libs/ libs/
COPY services/retrieval/ services/retrieval/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package sourcerer-retrieval

# --- runtime: same Python base as the builder, without uv or build layers ---
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/srv/.venv/bin:$PATH"

# Same paths as the builder: sourcerer-core is installed editable from /srv/libs.
COPY --from=builder /srv/.venv /srv/.venv
COPY --from=builder /srv/libs /srv/libs
COPY --from=builder /srv/services/retrieval /srv/services/retrieval

WORKDIR /srv/services/retrieval
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
