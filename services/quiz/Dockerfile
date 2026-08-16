# Build context: repo root
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /srv

# Workspace manifests only — cached until a lockfile/pyproject changes.
COPY pyproject.toml uv.lock ./
COPY libs/sourcerer-core/pyproject.toml libs/sourcerer-core/
COPY services/gateway/pyproject.toml services/gateway/
COPY services/ingestion/pyproject.toml services/ingestion/
COPY services/retrieval/pyproject.toml services/retrieval/
COPY services/quiz/pyproject.toml services/quiz/

# Third-party deps first (cached), then workspace members.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package sourcerer-quiz --no-install-workspace

COPY libs/ libs/
COPY services/quiz/ services/quiz/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package sourcerer-quiz

ENV PATH="/srv/.venv/bin:$PATH"
WORKDIR /srv/services/quiz
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
