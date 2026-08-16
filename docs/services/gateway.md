# Gateway Service

`services/gateway` — the single public entry point (published on **:8001**).

## Responsibilities

- Reverse-proxy every `/api/v1/*` request to the owning service with **full streaming passthrough** (SSE-safe: bytes are forwarded as they arrive)
- Aggregate `/health` across all services
- CORS for the frontend origin

## Route table

| Prefix | Upstream |
|---|---|
| `/api/v1/ingest` | `INGESTION_URL` |
| `/api/v1/retrieve`, `/api/v1/chat` | `RETRIEVAL_URL` |
| `/api/v1/quiz` | `QUIZ_URL` |

## Configuration (env)

| Variable | Default | Purpose |
|---|---|---|
| `INGESTION_URL` | `http://localhost:8010` | Ingestion service base URL |
| `RETRIEVAL_URL` | `http://localhost:8011` | Retrieval service base URL |
| `QUIZ_URL` | `http://localhost:8012` | Quiz service base URL |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

## Health aggregation

```bash
curl http://localhost:8001/health
```

```json
{
  "status": "ok",
  "gateway": "ok",
  "services": {
    "ingestion": {"status": "ok", "service": "ingestion"},
    "retrieval": {"status": "ok", "service": "retrieval"},
    "quiz": {"status": "ok", "service": "quiz"}
  }
}
```

`status` is `degraded` when any service is down; individual entries report `down` with the error type.
