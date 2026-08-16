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

# Gateway only needs third-party deps; it is run straight from source.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package sourcerer-gateway --no-install-workspace

# --- runtime: same Python base as the builder, without uv or build layers ---
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/srv/.venv/bin:$PATH"

RUN useradd --create-home --uid 10001 app
COPY --from=builder --chown=app:app /srv/.venv /srv/.venv
COPY --chown=app:app services/gateway/ /srv/services/gateway/

USER app
WORKDIR /srv/services/gateway
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
