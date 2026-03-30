# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG TORCH_EXTRA_INDEX=

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -n "$TORCH_EXTRA_INDEX" ]; then \
        uv sync --no-dev --extra-index-url "$TORCH_EXTRA_INDEX"; \
    else \
        uv sync --no-dev; \
    fi

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]