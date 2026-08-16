"""Sourcerer API Gateway.

Single public entry point for all backend services:

    /api/v1/ingest/*            -> ingestion service
    /api/v1/retrieve*, /chat*   -> retrieval service
    /api/v1/quiz/*              -> quiz service
    /api/v1/portal/*            -> portal service (resource portal)
    /health                     -> aggregate health of all services

Plain reverse proxy over httpx with full streaming passthrough (SSE-safe):
response bytes are forwarded as they arrive, never buffered.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

INGESTION_URL = os.getenv("INGESTION_URL", "http://localhost:8010")
RETRIEVAL_URL = os.getenv("RETRIEVAL_URL", "http://localhost:8011")
QUIZ_URL = os.getenv("QUIZ_URL", "http://localhost:8012")
PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8013")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

SERVICES = {
    "ingestion": INGESTION_URL,
    "retrieval": RETRIEVAL_URL,
    "quiz": QUIZ_URL,
    "portal": PORTAL_URL,
}

# Longest-prefix-first route table.
ROUTE_TABLE: list[tuple[str, str]] = [
    ("/api/v1/ingest", INGESTION_URL),
    ("/api/v1/retrieve", RETRIEVAL_URL),
    ("/api/v1/chat", RETRIEVAL_URL),
    ("/api/v1/quiz", QUIZ_URL),
    ("/api/v1/portal", PORTAL_URL),
]

# Hop-by-hop headers must not be forwarded.
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No read timeout: SSE streams and slow model pipelines stay open.
    app.state.client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=None, write=30.0, pool=None)
    )
    yield
    await app.state.client.aclose()


app = FastAPI(title="Sourcerer Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_upstream(path: str) -> str | None:
    for prefix, base in ROUTE_TABLE:
        if path.startswith(prefix):
            return base
    return None


@app.get("/health")
async def aggregate_health(request: Request) -> JSONResponse:
    """Fan out to every service's /health and aggregate the results."""
    client: httpx.AsyncClient = request.app.state.client

    async def check(name: str, base: str) -> tuple[str, dict]:
        try:
            resp = await client.get(f"{base}/health", timeout=5.0)
            body = resp.json() if resp.status_code == 200 else {}
            return name, {
                "status": "ok" if resp.status_code == 200 else "error",
                **({k: v for k, v in body.items() if k != "status"}),
            }
        except Exception as exc:  # noqa: BLE001 - report any failure as down
            return name, {"status": "down", "error": type(exc).__name__}

    results = dict(
        await asyncio.gather(*(check(n, b) for n, b in SERVICES.items()))
    )
    overall = "ok" if all(r["status"] == "ok" for r in results.values()) else "degraded"
    return JSONResponse({"status": overall, "gateway": "ok", "services": results})


@app.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy(request: Request, path: str):
    """Stream any /api/v1 request to the owning service."""
    full_path = f"/api/v1/{path}"
    upstream = _resolve_upstream(full_path)
    if upstream is None:
        return JSONResponse({"detail": "Unknown route"}, status_code=404)

    client: httpx.AsyncClient = request.app.state.client
    url = f"{upstream}{full_path}"
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP
    }

    upstream_request = client.build_request(
        request.method,
        url,
        headers=headers,
        params=request.query_params,
        content=request.stream(),
    )

    try:
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.ConnectError:
        logger.error("Upstream unreachable: %s", url)
        return JSONResponse(
            {"detail": f"Service unavailable: {upstream}"}, status_code=503
        )

    response = StreamingResponse(
        upstream_response.aiter_raw(),
        status_code=upstream_response.status_code,
        background=BackgroundTask(upstream_response.aclose),
    )
    # Rebuild headers from multi_items(): a dict would collapse duplicate
    # headers (multiple Set-Cookie lines become one comma-joined mess that
    # browsers reject). aiter_raw() forwards bytes verbatim, so the upstream
    # Content-Length stays valid — keep it (video 206 seeking needs it).
    response.raw_headers = [
        (k.encode("latin-1"), v.encode("latin-1"))
        for k, v in upstream_response.headers.multi_items()
        if k.lower() not in HOP_BY_HOP or k.lower() == "content-length"
    ]
    return response
