"""Portal service entry point.

Sourcerer as the face of the owner's Google Drive: Google sign-in, a
metadata-only catalog of the resource library, timed access requests/grants,
and access-checked in-app content viewing. No ingestion, no vector store —
this service never calls any paid API.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes.auth import router as auth_router
from sourcerer_core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Sourcerer Portal Service",
    description="Google Drive resource portal: auth, catalog, grants, viewing.",
    version="1.0.0",
)

_ALLOWED_ORIGINS = {
    origin.strip()
    for origin in settings.PORTAL_ALLOWED_ORIGINS.split(",")
    if origin.strip()
}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    """Reject state-changing cross-origin requests (belt-and-braces vs Lax)."""
    origin = request.headers.get("origin")
    if request.method not in _SAFE_METHODS and origin and origin not in _ALLOWED_ORIGINS:
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    return await call_next(request)


app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "portal"}
