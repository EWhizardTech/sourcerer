# Dockerfile  (your real one, replaces current)
FROM premdharshan/sourcerer-base:latest

WORKDIR /app

# Only app code copied here — no dep install
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]